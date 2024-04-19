use gnuplot::{AutoOption, AxesCommon, Color, Figure, LineWidth};

fn main() {
    let mut plots = Plots { plots: Vec::new() };

    plots.add("id", pareen::id());
    plots.add("lerp between 2 and 4", pareen::lerp(2.0, 4.0));
    plots.add(
        "dynamic lerp between sin^2 and cos",
        pareen::circle().sin().powi(2).lerp(pareen::circle().cos()),
    );
    plots.add(
        "dynamic lerp, squeezed into [0.5 .. 1]",
        pareen::circle()
            .sin()
            .powi(2)
            .lerp(pareen::circle().cos())
            .squeeze_and_surround(0.5..=1.0, 0.0),
    );
    plots.add(
        "switch from 1 to 2 at time=0.5",
        pareen::constant(1.0).switch(0.5, 2.0),
    );

    #[cfg(feature = "easer")]
    plots.add(
        "ease transition from 2 to a proportional anim",
        pareen::constant(2.0).seq_ease_in_out(
            0.5,
            easer::functions::Cubic,
            0.3,
            pareen::prop(1.0f32),
        ),
    );

    plots.show_gnuplot();
}

fn sample(
    n: usize,
    max_t: f32,
    anim: pareen::Anim<impl pareen::Fun<T = f32, V = f32>>,
) -> (Vec<f32>, Vec<f32>) {
    let mut ts = Vec::new();
    let mut vs = Vec::new();

    for i in 0..=n {
        let time = i as f32 / n as f32 * max_t;
        let value = anim.eval(time);

        ts.push(time);
        vs.push(value);
    }

    (ts, vs)
}

struct Plot {
    name: &'static str,
    ts: Vec<f32>,
    vs: Vec<f32>,
}

struct Plots {
    plots: Vec<Plot>,
}

impl Plots {
    fn add(&mut self, name: &'static str, anim: pareen::Anim<impl pareen::Fun<T = f32, V = f32>>) {
        let (ts, vs) = sample(1000, 1.0, anim);

        self.plots.push(Plot { name, ts, vs });
    }

    fn show_gnuplot(&self) {
        let mut figure = Figure::new();

        // Show plots in a square rows/columns layout
        let n_cols = (self.plots.len() as f32).sqrt() as u32;
        let n_rows = (self.plots.len() as f32).sqrt().ceil() as u32;

        for (i, plot) in self.plots.iter().enumerate() {
            figure
                .axes2d()
                .lines(&plot.ts, &plot.vs, &[Color("blue"), LineWidth(3.0)])
                .set_title(&plot.name, &[])
                .set_x_label("time", &[])
                .set_y_label("value", &[])
                .set_x_ticks(Some((AutoOption::Fix(0.5), 0)), &[], &[])
                .set_y_ticks(Some((AutoOption::Fix(0.5), 0)), &[], &[])
                .set_pos_grid(n_rows, n_cols, i as u32);
        }

        figure.show().unwrap();
    }
}
