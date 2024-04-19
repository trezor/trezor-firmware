use core::ops::{Add, Div, Mul};

use num_traits::{float::FloatCore, AsPrimitive, Zero};

use crate::{Anim, AnimWithDur, Fun};

impl<F> AnimWithDur<F>
where
    F: Fun<T = usize>,
{
    pub fn fold<B, G>(&self, init: B, mut f: G) -> B
    where
        G: FnMut(B, F::V) -> B,
    {
        let mut b = init;

        for t in 0..self.1 {
            b = f(b, self.0.eval(t))
        }

        b
    }
}

impl<F> AnimWithDur<F>
where
    F: Fun<T = usize>,
    F::V: Add<Output = F::V> + Zero,
{
    pub fn sum(&self) -> F::V {
        self.fold(Zero::zero(), |a, b| a + b)
    }
}

impl<F> AnimWithDur<F>
where
    F: Fun<T = usize>,
    F::T: Clone,
    F::V: 'static + Add<Output = F::V> + Div<Output = F::V> + Zero + Copy,
    usize: AsPrimitive<F::V>,
{
    pub fn mean(&self) -> F::V {
        let len = self.1.clone().as_();
        self.sum() / len
    }
}

#[derive(Debug, Clone)]
pub struct Line<V> {
    pub y_intercept: V,
    pub slope: V,
}

impl<V> Fun for Line<V>
where
    V: Add<Output = V> + Mul<Output = V> + Clone,
{
    type T = V;
    type V = V;

    fn eval(&self, t: V) -> V {
        self.y_intercept.clone() + self.slope.clone() * t
    }
}

pub fn simple_linear_regression_with_slope<V, F, A>(slope: V, values: A) -> Anim<Line<V>>
where
    V: 'static + FloatCore + Copy,
    F: Fun<T = usize, V = (V, V)>,
    A: Into<AnimWithDur<F>>,
    usize: AsPrimitive<V>,
{
    // https://en.wikipedia.org/wiki/Simple_linear_regression#Fitting_the_regression_line
    let values = values.into();
    let (x, y) = values.unzip();
    let x_mean = x.as_ref().mean();
    let y_mean = y.as_ref().mean();

    let y_intercept = y_mean - slope * x_mean;

    Anim(Line { y_intercept, slope })
}

pub fn simple_linear_regression<V, F, A>(values: A) -> Anim<Line<V>>
where
    V: 'static + FloatCore + Copy,
    F: Fun<T = usize, V = (V, V)>,
    A: Into<AnimWithDur<F>>,
    usize: AsPrimitive<V>,
{
    // https://en.wikipedia.org/wiki/Simple_linear_regression#Fitting_the_regression_line
    let values = values.into();
    let (x, y) = values.unzip();
    let x_mean = x.as_ref().mean();
    let y_mean = y.as_ref().mean();
    let numerator = values
        .as_ref()
        .map(|(x, y)| (x - x_mean) * (y - y_mean))
        .sum();
    let denominator = x.as_ref().map(|x| (x - x_mean) * (x - x_mean)).sum();
    let slope = numerator / denominator;

    let y_intercept = y_mean - slope * x_mean;

    Anim(Line { y_intercept, slope })
}

#[cfg(all(test, feature = "alloc"))]
mod tests {
    use assert_approx_eq::assert_approx_eq;
    extern crate alloc;
    use alloc::vec;

    use super::simple_linear_regression;

    #[test]
    fn test_perfect_regression() {
        let straight_line = vec![(1.0, 1.0), (2.0, 2.0)];
        let line = simple_linear_regression(straight_line.as_slice());
        assert_approx_eq!(line.eval(1.0), 1.0f64);
        assert_approx_eq!(line.eval(10.0), 10.0);
        assert_approx_eq!(line.eval(-10.0), -10.0);
    }

    #[test]
    fn test_negative_perfect_regression() {
        let straight_line = vec![(1.0, -1.0), (2.0, -2.0)];
        let line = simple_linear_regression(straight_line.as_slice());
        assert_approx_eq!(line.eval(1.0), -1.0f64);
        assert_approx_eq!(line.eval(10.0), -10.0);
        assert_approx_eq!(line.eval(-10.0), 10.0);
    }
}
