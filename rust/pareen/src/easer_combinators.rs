use num_traits::Float;

use easer::functions::Easing;

use crate::{fun, Anim, Fun};

impl<V, F> Anim<F>
where
    V: Float,
    F: Fun<T = V, V = V>,
{
    fn seq_ease<G, H, A>(
        self,
        self_end: V,
        ease: impl Fn(V, V, V) -> Anim<G>,
        ease_duration: V,
        next: A,
    ) -> Anim<impl Fun<T = V, V = V>>
    where
        G: Fun<T = V, V = V>,
        H: Fun<T = V, V = V>,
        A: Into<Anim<H>>,
    {
        let next = next.into();

        let ease_start_value = self.eval(self_end);
        let ease_end_value = next.eval(V::zero());
        let ease_delta = ease_end_value - ease_start_value;
        let ease = ease(ease_start_value, ease_delta, ease_duration);

        self.seq(self_end, ease).seq(self_end + ease_duration, next)
    }

    /// Play two animations in sequence, transitioning between them with an
    /// easing-in function from
    /// [`easer`](https://docs.rs/easer/0.2.1/easer/index.html).
    ///
    /// This is only available when enabling the `easer` feature for `pareen`.
    ///
    /// The values of `self` at `self_end` and of `next` at time zero are used
    /// to determine the parameters of the easing function.
    ///
    /// Note that, as with [`seq`](struct.Anim.html#method.seq), the `next`
    /// animation will see time starting at zero once it plays.
    ///
    /// # Arguments
    ///
    /// * `self_end` - Time at which the `self` animation is to stop.
    /// * `_easing` - A struct implementing
    ///     [`easer::functions::Easing`](https://docs.rs/easer/0.2.1/easer/functions/trait.Easing.html).
    ///     This determines the easing function that will be used for the
    ///     transition. It is passed as a parameter here to simplify type
    ///     inference.
    /// * `ease_duration` - The amount of time to use for transitioning to `next`.
    /// * `next` - The animation to play after transitioning.
    ///
    /// # Example
    ///
    /// See [`seq_ease_in_out`](struct.Anim.html#method.seq_ease_in_out) for an example.
    pub fn seq_ease_in<E, G, A>(
        self,
        self_end: V,
        _easing: E,
        ease_duration: V,
        next: A,
    ) -> Anim<impl Fun<T = V, V = V>>
    where
        E: Easing<V>,
        G: Fun<T = V, V = V>,
        A: Into<Anim<G>>,
    {
        self.seq_ease(self_end, ease_in::<E, V>, ease_duration, next)
    }

    /// Play two animations in sequence, transitioning between them with an
    /// easing-out function from
    /// [`easer`](https://docs.rs/easer/0.2.1/easer/index.html).
    ///
    /// This is only available when enabling the `easer` feature for `pareen`.
    ///
    /// The values of `self` at `self_end` and of `next` at time zero are used
    /// to determine the parameters of the easing function.
    ///
    /// Note that, as with [`seq`](struct.Anim.html#method.seq), the `next`
    /// animation will see time starting at zero once it plays.
    ///
    /// # Arguments
    ///
    /// * `self_end` - Time at which the `self` animation is to stop.
    /// * `_easing` - A struct implementing
    ///     [`easer::functions::Easing`](https://docs.rs/easer/0.2.1/easer/functions/trait.Easing.html).
    ///     This determines the easing function that will be used for the
    ///     transition. It is passed as a parameter here to simplify type
    ///     inference.
    /// * `ease_duration` - The amount of time to use for transitioning to `next`.
    /// * `next` - The animation to play after transitioning.
    ///
    /// # Example
    ///
    /// See [`seq_ease_in_out`](struct.Anim.html#method.seq_ease_in_out) for an example.
    pub fn seq_ease_out<E, G, A>(
        self,
        self_end: V,
        _: E,
        ease_duration: V,
        next: A,
    ) -> Anim<impl Fun<T = V, V = V>>
    where
        E: Easing<V>,
        G: Fun<T = V, V = V>,
        A: Into<Anim<G>>,
    {
        self.seq_ease(self_end, ease_out::<E, V>, ease_duration, next)
    }

    /// Play two animations in sequence, transitioning between them with an
    /// easing-in-out function from
    /// [`easer`](https://docs.rs/easer/0.2.1/easer/index.html).
    ///
    /// This is only available when enabling the `easer` feature for `pareen`.
    ///
    /// The values of `self` at `self_end` and of `next` at time zero are used
    /// to determine the parameters of the easing function.
    ///
    /// Note that, as with [`seq`](struct.Anim.html#method.seq), the `next`
    /// animation will see time starting at zero once it plays.
    ///
    /// # Arguments
    ///
    /// * `self_end` - Time at which the `self` animation is to stop.
    /// * `_easing` - A struct implementing
    ///     [`easer::functions::Easing`](https://docs.rs/easer/0.2.1/easer/functions/trait.Easing.html).
    ///     This determines the easing function that will be used for the
    ///     transition. It is passed as a parameter here to simplify type
    ///     inference.
    /// * `ease_duration` - The amount of time to use for transitioning to `next`.
    /// * `next` - The animation to play after transitioning.
    ///
    /// # Example
    ///
    /// Play a constant value until time `0.5`, then transition for `0.3`
    /// time units, using a cubic function, into a second animation:
    /// ```
    /// let first_anim = pareen::constant(2.0);
    /// let second_anim = pareen::prop(1.0f32);
    /// let anim = first_anim.seq_ease_in_out(
    ///     0.5,
    ///     easer::functions::Cubic,
    ///     0.3,
    ///     second_anim,
    /// );
    /// ```
    /// The animation will look like this:
    ///
    /// ![plot for seq_ease_in_out](https://raw.githubusercontent.com/leod/pareen/master/images/seq_ease_in_out.png)
    pub fn seq_ease_in_out<E, G, A>(
        self,
        self_end: V,
        _: E,
        ease_duration: V,
        next: A,
    ) -> Anim<impl Fun<T = V, V = V>>
    where
        E: Easing<V>,
        G: Fun<T = V, V = V>,
        A: Into<Anim<G>>,
    {
        self.seq_ease(self_end, ease_in_out::<E, V>, ease_duration, next)
    }
}

/// Integrate an easing-in function from the
/// [`easer`](https://docs.rs/easer/0.2.1/easer/index.html) library.
///
/// This is only available when enabling the `easer` feature for `pareen`.
///
/// # Arguments
///
/// * `start` - The start value for the easing function.
/// * `delta` - The change in the value from beginning to end time.
/// * `duration` - The total time between beginning and end.
///
/// # See also
/// Documentation for [`easer::functions::Easing`](https://docs.rs/easer/0.2.1/easer/functions/trait.Easing.html).
pub fn ease_in<E, V>(start: V, delta: V, duration: V) -> Anim<impl Fun<T = V, V = V>>
where
    V: Float,
    E: Easing<V>,
{
    fun(move |t| E::ease_in(t, start, delta, duration))
}

/// Integrate an easing-out function from the
/// [`easer`](https://docs.rs/easer/0.2.1/easer/index.html) library.
///
/// This is only available when enabling the `easer` feature for `pareen`.
///
/// # Arguments
///
/// * `start` - The start value for the easing function.
/// * `delta` - The change in the value from beginning to end time.
/// * `duration` - The total time between beginning and end.
///
/// # See also
/// Documentation for [`easer::functions::Easing`](https://docs.rs/easer/0.2.1/easer/functions/trait.Easing.html).
pub fn ease_out<E, V>(start: V, delta: V, duration: V) -> Anim<impl Fun<T = V, V = V>>
where
    V: Float,
    E: Easing<V>,
{
    fun(move |t| E::ease_out(t, start, delta, duration))
}

/// Integrate an easing-in-out function from the
/// [`easer`](https://docs.rs/easer/0.2.1/easer/index.html) library.
///
/// This is only available when enabling the `easer` feature for `pareen`.
///
/// # Arguments
///
/// * `start` - The start value for the easing function.
/// * `delta` - The change in the value from beginning to end time.
/// * `duration` - The total time between beginning and end.
///
/// # See also
/// Documentation for [`easer::functions::Easing`](https://docs.rs/easer/0.2.1/easer/functions/trait.Easing.html).
pub fn ease_in_out<E, V>(start: V, delta: V, duration: V) -> Anim<impl Fun<T = V, V = V>>
where
    V: Float,
    E: Easing<V>,
{
    fun(move |t| E::ease_in_out(t, start, delta, duration))
}
