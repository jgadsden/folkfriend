use crate::decode::pitch_model::PitchModel;
use crate::decode::tempo_model::TempoModel;
use crate::decode::types::{Duration, Pitch, PitchInterval};

#[derive(Copy, Clone, Debug)]
pub struct Proposal {
    pub prev_proposal_id: usize,
    pub pitch: Pitch,
    pub score: f32,
    pub duration: Duration,
    pub pitch_changed: bool,
}

impl Proposal {
    pub fn compute_child_proposal(
        &self,
        pitch_model: &PitchModel,
        tempo_model: &TempoModel,
        parent_id: usize,
        child_pitch: Pitch,
        child_energy: f32
    ) -> Proposal {
        // Compute a proposal at time t given the proposal and proposal id at time
        //  t-1, the pitch at time t, and the spectral energy at that pitch and
        //  time.

        let mut new_score = self.score;
        new_score += child_energy;

        let interval = child_pitch as PitchInterval - self.pitch as PitchInterval;
        let pitch_changed: bool = interval != 0;
        let duration: Duration;

        if pitch_changed {
            // This is the same for each value of the inner loop that calls this
            //   function. This is a performance optimisation.
            new_score += tempo_model.score(&self.duration);
            new_score += pitch_model.score(&interval);
            duration = 1;
        } else {
            duration = self.duration + 1;
        }

        return Proposal {
            prev_proposal_id: parent_id,
            pitch: child_pitch,
            score: new_score,
            duration: duration,
            pitch_changed: pitch_changed,
        };
    }
}