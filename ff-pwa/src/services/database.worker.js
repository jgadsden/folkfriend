import Dexie from "dexie";

class DatabaseService {
    // MAX_NUD_AGE = 28;   // 28 days = 4 weeks
    MAX_NUD_AGE = 0;   // 0 = always use latest version

    constructor() {
        console.debug(`${this.constructor.name} init`);

        let db = new Dexie('folkfriend');
        // Setup database schema
        db.version(1).stores({
            /* Version string to track when the Non-User Data was updated last */
            NUDVersion: 'key',    // We always store this at key zero. We only need one entry in this table.

            /* Non-user data */
            // settings: '&setting, tune, name, type, meter, mode',    // 'abc' added but not indexed
            settings: '&setting, tune, name',    // 'abc, type, meter, mode' added but not indexed for performance reasons
            aliases: '&tune, *aliases',

            // Generic table for our bulky objects. Bulky objects are NOT!!! indexed.
            // These are the shard meta JSON and the partitioned shards pngs in base 64.
            bulk: 'name',

            /* User data */
            // transcriptions: '++id, timestamp, name',  // 'midis' added but not indexed
            // history: '++id, timestamp, tune'   // 'midis' added but not indexed
        });

        this.db = db;
        this.networkProgress = {};

        // We use a promise to track whether or not some data was detected,
        //  so that the user only has to wait for the shards data to download
        //  if none is detected already.
        this.hasData = new Promise((resolve) => {
            this.confirmHasData = () => {
                console.debug('Confirmed query engine data exists');
                resolve();
            };
        });

        this.checkForUpdates().then(hasUpdated => {
            console.debug(`Non-user data has ${hasUpdated === true ? '' : 'not '}updated`);
        });
    }

    async checkForUpdates() {
        let NUDVersionLocal = await this.getNUDVersionLocal();
        let NUDMetaRemote = await this.getNUDMetaRemote();
        let NUDVersionRemote = NUDMetaRemote['v'];
        let NUDSize = NUDMetaRemote['size'];

        console.debug('NUDVersionLocal', NUDVersionLocal);
        console.debug('NUDMetaRemote', NUDMetaRemote);

        let canUpdate = NUDVersionRemote !== null && NUDVersionRemote !== NUDVersionLocal;

        if (NUDVersionLocal !== null) {
            this.confirmHasData();
        }

        if (NUDVersionRemote === null) {
            console.warn('Could not find NUDVersionRemote');
        }
        if (!canUpdate) {
            return;
        }

        let NUDExpired = this.daysSince2020() - NUDVersionLocal > this.MAX_NUD_AGE;

        if (NUDVersionLocal === null) {
            console.debug('NUData has not been loaded, attempting to update');
            try {
                await this.updateNonUserData(NUDVersionRemote, NUDSize);
                this.confirmHasData();
                return true;
            } catch (e) {
                // This is a very bad state to be in.
                //  No tune database was found and we failed to install one.
                //  This is not a critical error but needs a graceful fallback.
                console.error(e);
            }
        } else if (NUDExpired) {
            console.debug('NUData has expired, attempting to update');
            try {
                await this.updateNonUserData(NUDVersionRemote, NUDSize);
                return true;
            } catch (e) {
                // This is a not so bad state to be in.
                //  A tune database was found but we failed to upgrade.
                //  This is only concerning if it keeps happening.
                console.warn(e);
            }
        }
    }

    async getNUDVersionLocal() {
        const versionObj = await this.db.NUDVersion.get(0);
        if (typeof versionObj === 'undefined') {
            // No install detected.
            return null;
        }
        return versionObj.v;
    }

    async getNUDMetaRemote() {
        try {
            let response = await fetch('http://192.168.0.19//nud-meta.json');
            return await response.json();
        } catch (e) {
            return {"v": null, "size": null};
        }
    }

    async getQueryEngineData() {
        await this.hasData;
        return {
            partitionsData: (await this.db.bulk.get("partitionsData")).value,
            shardMeta: (await this.db.bulk.get("shardMeta")).value
        };
    }

    async updateNonUserData(NUDVersionRemote, NUDSize) {
        // We now fetch the big data file.
        const NUData = await this.fetchJSONWithProgress(
            'NUData',
            'http://192.168.0.19/folkfriend-non-user-data.json',
            NUDSize);

        // The JSON file stores the big PNG shard partitions as base64 (because
        //  it's easy to transfer in JSON). However if we send megabyte size
        //  base64 strings to the main thread to decode and load into an
        //  HTMLImageElement every time we want to instantiate a QueryEngine
        //  then we hammer the UI framerate. The solution is to convert from
        //  Base64 to blob, once, inside this worker, and store the blob inside
        //  IndexedDB (using Dexie).
        for (let i = 0; i < NUData['shard-partitions'].length; i++) {
            // data:image/png;base64,<............................>
            const fetchedPartition = await fetch(NUData['shard-partitions'][i]);
            NUData['shard-partitions'][i] = await fetchedPartition.blob();
        }

        // Now use the big data file to update the IDB.
        //  This is a transaction so either it all works or it all rejects (thanks Dexie).
        await this.db.transaction('rw', [
            this.db.NUDVersion,
            this.db.settings,
            this.db.aliases,
            this.db.bulk
        ], function () {
            /* Update bulk data objects */
            this.db.bulk.put({
                name: 'shardMeta',
                value: NUData['shard-to-settings']
            });

            this.db.bulk.put({
                name: 'partitionsData',
                value: NUData['shard-partitions']
            });

            /* Update tune settings */
            this.db.settings.bulkPut(NUData['tunes']);

            /* Update aliases */
            this.db.aliases.bulkPut(NUData['aliases']);

            /* Now bump version */
            this.db.NUDVersion.put({
                key: 0,
                v: NUDVersionRemote
            });
        });
        console.log('complete');
    }

    async fetchJSONWithProgress(requestLabel, url, size) {
        // Taken directly from
        //  https://javascript.info/fetch-progress

        // Step 1: start the fetch and obtain a reader
        let response = await fetch(url);

        const reader = response.body.getReader();

        // Step 2: get total length
        //  Prefer to pass size in from metadata file as gzip means
        //  there's a mismatch between content length and received length
        if (typeof size === 'undefined') {
            size = +response.headers.get('Content-Length');
        }

        // Step 3: read the data
        let receivedLength = 0; // received that many bytes at the moment
        let chunks = []; // array of received binary chunks (comprises the body)

        // eslint-disable-next-line no-constant-condition
        while (true) {
            let {done, value} = await reader.read();

            if (done) {
                break;
            }

            chunks.push(value);
            receivedLength += value.length;

            this.networkProgress[requestLabel] = 100 * receivedLength / size;
        }

        // Step 4: concatenate chunks into single Uint8Array
        let chunksAll = new Uint8Array(receivedLength); // (4.1)
        let position = 0;
        for (let chunk of chunks) {
            chunksAll.set(chunk, position); // (4.2)
            position += chunk.length;
        }

        // Step 5: decode into a string
        let result = new TextDecoder('utf-8').decode(chunksAll);

        // We're done!
        return JSON.parse(result);
    }

    daysSince2020() {
        const unixMs = Date.now();
        const unixS = Math.round(unixMs / 1000);

        // 1577836800 = 2020-01-01T00:00:00+00:00 in ISO 8601
        const secsSince2020 = unixS - 1577836800;
        const daysSince2020 = Math.round(secsSince2020 / (24 * 3600));

        // NO time travelling >:c
        return Math.max(0, daysSince2020);
    }

    async tunesFromQueryResults(results) {
        return this.db.settings.bulkGet(results.map(({setting}) => setting));
    }
}

const ds = new DatabaseService();
export default ds;
