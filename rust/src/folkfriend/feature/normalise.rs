use crate::folkfriend::ff_config;

use crate::folkfriend::feature::types::Features;

pub trait Normalisable {
    fn total_energy(&self) -> f32;
    fn normalise_energy(&mut self);
}

impl Normalisable for Features {
    fn total_energy(&self) -> f32 {
        let mut cum_tot: f32 = 0.;
        for i in 0..self.len() {
            for j in 0..ff_config::MIDI_NUM {
                cum_tot += &self[i][j as usize];
            }
        }
        return cum_tot;
    }

    fn normalise_energy(&mut self) {
        // Normalises energy to have on average 1 AU per frame.
        let tot_energy = self.total_energy();
        let norm_const = self.len() as f32 / tot_energy;
        for i in 0..self.len() {
            for j in 0..ff_config::MIDI_NUM {
                self[i][j as usize] *= norm_const;
            }
        }
    }
}