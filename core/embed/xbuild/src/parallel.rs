use std::{
    env,
    sync::{Arc, Mutex, mpsc},
    thread,
};

use color_eyre::Result;

use crate::helpers::measure_time;

/// Executes a function in parallel across multiple worker threads for a
/// collection of input units.
///
/// The function `func` is applied to each unit in `units`, and the results are
/// collected and returned as a vector.
///
/// The number of worker threads is determined based on environment variables
/// and system capabilities.
pub fn run_parallel<U, A>(
    units: impl IntoIterator<Item = U>,
    func: impl Fn(&U) -> Result<A> + Send + Sync,
) -> Result<Vec<A>>
where
    U: Send + Sync,
    A: Send,
{
    let (work_tx, work_rx) = mpsc::channel::<U>();
    let (result_tx, result_rx) = mpsc::channel::<Result<A>>();
    let work_rx = Arc::new(Mutex::new(work_rx));

    let mut unit_count = 0;
    for unit in units {
        work_tx
            .send(unit)
            .expect("work channel closed unexpectedly");
        unit_count += 1;
    }

    // Close the work channel so workers will exit when all units are consumed.
    drop(work_tx);

    let n_jobs = optimal_parallel_job_count(unit_count);

    eprintln!(
        "$$ Parallel processing of {} units with {} worker threads",
        unit_count, n_jobs
    );

    measure_time("@@ Parallel job finished in", || {
        thread::scope(|s| {
            for _ in 0..n_jobs {
                let work_rx = Arc::clone(&work_rx);
                let result_tx = result_tx.clone();
                let func = &func;

                s.spawn(move || {
                    loop {
                        let unit = match work_rx.lock().expect("work queue poisoned").recv() {
                            Ok(unit) => unit,
                            Err(_) => break,
                        };
                        if result_tx.send(func(&unit)).is_err() {
                            break;
                        }
                    }
                });
            }
        })
    });

    // Drop the main thread's sender so the result channel closes
    // now that all workers have joined and dropped their clones.
    drop(result_tx);

    result_rx.iter().collect::<Result<Vec<A>>>()
}

// Determines the optimal number of parallel jobs based on
// environment variable and system capabilities.
fn optimal_parallel_job_count(unit_count: usize) -> usize {
    env::var("NUM_JOBS")
        .ok()
        .and_then(|v| v.parse::<usize>().ok())
        .filter(|v| *v > 0)
        .unwrap_or_else(|| {
            thread::available_parallelism()
                .map(usize::from)
                .unwrap_or(1)
        })
        .max(1)
        .min(unit_count.max(1))
}
