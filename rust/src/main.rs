mod dataset;
mod debug_features;
mod folkfriend;

use folkfriend::FolkFriend;

// use crate::folkfriend::index::schema::*;
use clap::{App, Arg};
use indicatif::ProgressBar;
use rayon::prelude::*;
use std::convert::TryInto;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;
use std::time::Instant;
use wav;
use std::fs;

fn main() {
    let now = Instant::now();

    let matches = App::new("FolkFriend")
        .version("3.0")
        .author("T.C. Wyllie <tom@wyllie.dev>")
        .about("Transcription and recognition of traditional instrumental folk music")
        .arg(
            Arg::new("command")
                .required(true)
                .possible_values(&["transcribe", "query", "name"]),
        )
        .arg(Arg::new("input").required(true))
        .get_matches();

    let command = matches.value_of("command").unwrap();
    let input = matches.value_of("input").unwrap().to_string();

    let mut ff = FolkFriend::new();
    let tune_index_json = get_tune_index_json();
    ff = ff.load_index_from_json_string(tune_index_json);

    if command == "name" {
        name_query(ff, input);
    } else if command == "transcribe" {
        process_audio_files(ff, input, false);
    } else if command == "query" {
        process_audio_files(ff, input, true);
    }

    eprintln!("FolkFriend finished in {:.2?}", now.elapsed());

    // for wav_path in 

    // if wav, push to list

    // if CSV, open all lines and push to list

    // now iterate through list and do the thing for each one

    // if let Some(ref args) = args.subcommand_matches("dataset") {
    //     let dataset_path = args.value_of("dataset-path").unwrap().to_string();
    //     let dataset_op = args.value_of("dataset-op").unwrap();

    //     match dataset_op {
    //         "transcribe" => {
    //             println!("transcribing")
    //         }
    //         "query" => bulk_query(&dataset_path),
    //         _ => {}
    //     }
    // }


}

fn process_audio_files(mut ff: FolkFriend, input: String, with_transcription_query: bool) {

    // Load file paths from arguments / input CSV file
    let input_is_csv = input.ends_with(".csv");
    let mut audio_file_paths: Vec<String> = Vec::new();

    if input.ends_with(".wav") {
        audio_file_paths = vec![input];
    } else if input_is_csv {
        audio_file_paths = get_audio_file_paths_from_csv(&input)
    } else {
        panic!(
            "Input path `{}` was invalid, please supply a .wav file, or a 
            .csv file of paths to .wav files",
            input
        )
    }

    for audio_file_path in audio_file_paths {
        if !audio_file_path.ends_with(".wav") {
            eprintln!("Skipping non .wav file `{}`", audio_file_path);
            return;
        }
    
        // println!("{}", audio_file_path);

        let (signal, sample_rate) = pcm_signal_from_wav(&audio_file_path);

        ff.set_sample_rate(sample_rate);
        ff.feed_entire_pcm_signal(signal);
        
        // TODO this is awful, fix
        let transcribed = ff.transcribe_pcm_buffer();
        ff = transcribed.0;
        let contour = transcribed.1;

        let results = ff.run_transcription_query(&contour).expect("something failed");
        println!("{:#?}", results);
    }

            

    // let decoder = folkfriend::decode::FeatureDecoder::new();
    
    // debug_features::save_features_as_img(&fe.features, &"debug-a.png".to_string());
    // debug_features::save_contour_as_img(&contour, &"debug-b.png".to_string());


}

fn pcm_signal_from_wav(wav_file_path: &String) -> (Vec<f32>, u32) {
    let mut inp_file = File::open(Path::new(&wav_file_path)).unwrap();
    let (header, data) = wav::read(&mut inp_file).unwrap();

    // let mut fe =
    //     folkfriend::feature::feature_extractor::FeatureExtractor::new(header.sampling_rate);
    let signal: Vec<i16> = data.try_into_sixteen().unwrap();

    let mut signal_f: Vec<f32> = vec![0.; signal.len()];
    for i in 0..signal.len() {
        signal_f[i] = (signal[i] as f32) / 32768.;
    }

    return (signal_f, header.sampling_rate);
}
    

fn get_audio_file_paths_from_csv(csv_path: &String) -> Vec<String> {
    let mut audio_file_paths = Vec::new();
    let file = File::open(csv_path).expect(&format!("File `{}` could not be opened", csv_path));
    let reader = BufReader::new(file);
    let mut lines: Vec<String> = reader
        .lines()
        .map(|l| l.expect("Could not parse line"))
        .collect();
    audio_file_paths.append(&mut lines);
    audio_file_paths
}

fn name_query(ff: FolkFriend, name: String) {
    let result = ff.run_name_query(&name).expect("Name query failed");

    for record in result {
        println!("{:?}", record.display_name);
    }
}

pub fn get_tune_index_json() -> String {
    // TODO auto pull from Github if local copy not found
    let path =
        "/home/tom/repos/folkfriend/scripts/index-builder/index-data/folkfriend-non-user-data.json";
    let data = fs::read_to_string(path).expect("Couldn't read index");
    return data;
}

// fn bulk_query(dataset_path: &String) {
//     let transcriptions = dataset::load_transcriptions(&dataset_path).unwrap();
//     let tune_index = folkfriend::index::load::load_from_path();
//     let tune_settings: TuneSettings = tune_index.settings;
//     let query_engine = folkfriend::query::QueryEngine::new(tune_settings);
//     let bar = ProgressBar::new(transcriptions.len().try_into().unwrap());

//     let ranks: Vec<usize> = transcriptions
//         .par_iter()
//         .map(|transcription| {
//             let query = &transcription.transcription;
//             let ranked_settings = query_engine.run_transcription_query(query);
//             let mut rank: usize = ranked_settings.len();

//             for (i, (tune_id, _, _)) in ranked_settings.iter().enumerate() {
//                 if *tune_id == transcription.tune_id {
//                     rank = i;
//                     break;
//                 }
//             }

//             bar.inc(1);

//             rank
//         })
//         .collect();
//     let mut bulk_output: Vec<dataset::TranscriptionRecordRanked> = Vec::new();
//     for (rank, transcription) in ranks.iter().zip(transcriptions) {
//         let ranked = dataset::TranscriptionRecordRanked {
//             rank: *rank,
//             rel_path: transcription.rel_path,
//             tune_id: transcription.tune_id,
//             name: transcription.name,
//             transcription: transcription.transcription,
//         };
//         bulk_output.push(ranked);
//     }

//     dataset::write_transcriptions_ranked(dataset_path, bulk_output).unwrap();

//     bar.finish();
// }
