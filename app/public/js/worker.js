import "/js/comlink.js";

import init, { FolkFriendWASM } from "/wasm/folkfriend.js";

class FolkFriendWASMWrapper {
    constructor() {
        this.folkfriendWASM = null;
        this.loadedWASM = new Promise(resolve => {
            this.setLoadedWASM = resolve;
        });

        init().then(() => {
            this.folkfriendWASM = new FolkFriendWASM();
            this.setLoadedWASM();
        })
    }

    async version(cb) {
        await this.loadedWASM;
        cb(this.folkfriendWASM.version());
    }

    async loadIndexFromJSONString(JSONString) {
        await this.loadedWASM;
        this.folkfriendWASM.load_index_from_json_string(JSONString);
    }
}

const folkfriendWASMWrapper = new FolkFriendWASMWrapper();
Comlink.expose(folkfriendWASMWrapper);
