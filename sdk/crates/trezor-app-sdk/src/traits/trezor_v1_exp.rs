pub mod trezor_v1 {
    use stabby::str::Str;
    use super::allocator::StaticAllocatorV1;
    use super::crypto::StaticCryptoV1;
    use super::syslog::StaticSyslogV1;
    #[deny(improper_ctypes_definitions)]
    pub trait TrezorApiV1: Send + Sync {
        extern "C" fn system_exit(&self) -> !;
        extern "C" fn system_exit_error<'a>(
            &self,
            title: Str<'a>,
            message: Str<'a>,
            footer: Str<'a>,
        ) -> !;
        extern "C" fn system_exit_fatal<'a>(
            &self,
            message: Str<'a>,
            file: Str<'a>,
            line: u32,
        ) -> !;
        extern "C" fn systick_ms(&self) -> u32;
        extern "C" fn sleep(&self, timeout_ms: u32);
    }
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    ///An stabby-generated item for [`TrezorApiV1`]
    #[repr(C)]
    pub struct StabbyVtableTrezorApiV1<'stabby_vt_lt> {
        ///An stabby-generated item for [`TrezorApiV1`]
        pub system_exit: stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                ) -> !,
                &'static (),
            >,
            (),
        >,
        ///An stabby-generated item for [`TrezorApiV1`]
        pub system_exit_error: stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt, 'a> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    Str<'a>,
                    Str<'a>,
                    Str<'a>,
                ) -> !,
                &'static (),
            >,
            stabby::abi::Union<
                stabby::abi::Union<stabby::abi::Union<(), Str<'static>>, Str<'static>>,
                Str<'static>,
            >,
        >,
        ///An stabby-generated item for [`TrezorApiV1`]
        pub system_exit_fatal: stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt, 'a> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    Str<'a>,
                    Str<'a>,
                    u32,
                ) -> !,
                &'static (),
            >,
            stabby::abi::Union<
                stabby::abi::Union<stabby::abi::Union<(), Str<'static>>, Str<'static>>,
                u32,
            >,
        >,
        ///An stabby-generated item for [`TrezorApiV1`]
        pub systick_ms: stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                ) -> u32,
                &'static (),
            >,
            u32,
        >,
        ///An stabby-generated item for [`TrezorApiV1`]
        pub sleep: stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    u32,
                ),
                &'static (),
            >,
            stabby::abi::Union<(), u32>,
        >,
    }
    #[automatically_derived]
    unsafe impl<'stabby_vt_lt> stabby::abi::IStable
    for StabbyVtableTrezorApiV1<'stabby_vt_lt>
    where
        stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<
                        stabby::abi::FieldPair<
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                    ) -> !,
                                    &'static (),
                                >,
                                (),
                            >,
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt, 'a> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                        Str<'a>,
                                        Str<'a>,
                                        Str<'a>,
                                    ) -> !,
                                    &'static (),
                                >,
                                stabby::abi::Union<
                                    stabby::abi::Union<
                                        stabby::abi::Union<(), Str<'static>>,
                                        Str<'static>,
                                    >,
                                    Str<'static>,
                                >,
                            >,
                        >,
                        stabby::abi::StableIf<
                            stabby::abi::StableLike<
                                for<'stabby_receiver_lt, 'a> extern "C" fn(
                                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                    ::core::marker::PhantomData<
                                        &'stabby_receiver_lt &'stabby_vt_lt (),
                                    >,
                                    Str<'a>,
                                    Str<'a>,
                                    u32,
                                ) -> !,
                                &'static (),
                            >,
                            stabby::abi::Union<
                                stabby::abi::Union<
                                    stabby::abi::Union<(), Str<'static>>,
                                    Str<'static>,
                                >,
                                u32,
                            >,
                        >,
                    >,
                    stabby::abi::StableIf<
                        stabby::abi::StableLike<
                            for<'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                            ) -> u32,
                            &'static (),
                        >,
                        u32,
                    >,
                >,
                stabby::abi::StableIf<
                    stabby::abi::StableLike<
                        for<'stabby_receiver_lt> extern "C" fn(
                            stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_vt_lt (),
                            >,
                            u32,
                        ),
                        &'static (),
                    >,
                    stabby::abi::Union<(), u32>,
                >,
            >,
        >: stabby::abi::IStable,
        stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    u32,
                ),
                &'static (),
            >,
            stabby::abi::Union<(), u32>,
        >: stabby::abi::IStable,
        stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                ) -> u32,
                &'static (),
            >,
            u32,
        >: stabby::abi::IStable,
        stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt, 'a> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    Str<'a>,
                    Str<'a>,
                    u32,
                ) -> !,
                &'static (),
            >,
            stabby::abi::Union<
                stabby::abi::Union<stabby::abi::Union<(), Str<'static>>, Str<'static>>,
                u32,
            >,
        >: stabby::abi::IStable,
        stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt, 'a> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    Str<'a>,
                    Str<'a>,
                    Str<'a>,
                ) -> !,
                &'static (),
            >,
            stabby::abi::Union<
                stabby::abi::Union<stabby::abi::Union<(), Str<'static>>, Str<'static>>,
                Str<'static>,
            >,
        >: stabby::abi::IStable,
        stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                ) -> !,
                &'static (),
            >,
            (),
        >: stabby::abi::IStable,
    {
        type ForbiddenValues = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<
                        stabby::abi::FieldPair<
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                    ) -> !,
                                    &'static (),
                                >,
                                (),
                            >,
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt, 'a> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                        Str<'a>,
                                        Str<'a>,
                                        Str<'a>,
                                    ) -> !,
                                    &'static (),
                                >,
                                stabby::abi::Union<
                                    stabby::abi::Union<
                                        stabby::abi::Union<(), Str<'static>>,
                                        Str<'static>,
                                    >,
                                    Str<'static>,
                                >,
                            >,
                        >,
                        stabby::abi::StableIf<
                            stabby::abi::StableLike<
                                for<'stabby_receiver_lt, 'a> extern "C" fn(
                                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                    ::core::marker::PhantomData<
                                        &'stabby_receiver_lt &'stabby_vt_lt (),
                                    >,
                                    Str<'a>,
                                    Str<'a>,
                                    u32,
                                ) -> !,
                                &'static (),
                            >,
                            stabby::abi::Union<
                                stabby::abi::Union<
                                    stabby::abi::Union<(), Str<'static>>,
                                    Str<'static>,
                                >,
                                u32,
                            >,
                        >,
                    >,
                    stabby::abi::StableIf<
                        stabby::abi::StableLike<
                            for<'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                            ) -> u32,
                            &'static (),
                        >,
                        u32,
                    >,
                >,
                stabby::abi::StableIf<
                    stabby::abi::StableLike<
                        for<'stabby_receiver_lt> extern "C" fn(
                            stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_vt_lt (),
                            >,
                            u32,
                        ),
                        &'static (),
                    >,
                    stabby::abi::Union<(), u32>,
                >,
            >,
        > as stabby::abi::IStable>::ForbiddenValues;
        type UnusedBits = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<
                        stabby::abi::FieldPair<
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                    ) -> !,
                                    &'static (),
                                >,
                                (),
                            >,
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt, 'a> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                        Str<'a>,
                                        Str<'a>,
                                        Str<'a>,
                                    ) -> !,
                                    &'static (),
                                >,
                                stabby::abi::Union<
                                    stabby::abi::Union<
                                        stabby::abi::Union<(), Str<'static>>,
                                        Str<'static>,
                                    >,
                                    Str<'static>,
                                >,
                            >,
                        >,
                        stabby::abi::StableIf<
                            stabby::abi::StableLike<
                                for<'stabby_receiver_lt, 'a> extern "C" fn(
                                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                    ::core::marker::PhantomData<
                                        &'stabby_receiver_lt &'stabby_vt_lt (),
                                    >,
                                    Str<'a>,
                                    Str<'a>,
                                    u32,
                                ) -> !,
                                &'static (),
                            >,
                            stabby::abi::Union<
                                stabby::abi::Union<
                                    stabby::abi::Union<(), Str<'static>>,
                                    Str<'static>,
                                >,
                                u32,
                            >,
                        >,
                    >,
                    stabby::abi::StableIf<
                        stabby::abi::StableLike<
                            for<'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                            ) -> u32,
                            &'static (),
                        >,
                        u32,
                    >,
                >,
                stabby::abi::StableIf<
                    stabby::abi::StableLike<
                        for<'stabby_receiver_lt> extern "C" fn(
                            stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_vt_lt (),
                            >,
                            u32,
                        ),
                        &'static (),
                    >,
                    stabby::abi::Union<(), u32>,
                >,
            >,
        > as stabby::abi::IStable>::UnusedBits;
        type Size = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<
                        stabby::abi::FieldPair<
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                    ) -> !,
                                    &'static (),
                                >,
                                (),
                            >,
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt, 'a> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                        Str<'a>,
                                        Str<'a>,
                                        Str<'a>,
                                    ) -> !,
                                    &'static (),
                                >,
                                stabby::abi::Union<
                                    stabby::abi::Union<
                                        stabby::abi::Union<(), Str<'static>>,
                                        Str<'static>,
                                    >,
                                    Str<'static>,
                                >,
                            >,
                        >,
                        stabby::abi::StableIf<
                            stabby::abi::StableLike<
                                for<'stabby_receiver_lt, 'a> extern "C" fn(
                                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                    ::core::marker::PhantomData<
                                        &'stabby_receiver_lt &'stabby_vt_lt (),
                                    >,
                                    Str<'a>,
                                    Str<'a>,
                                    u32,
                                ) -> !,
                                &'static (),
                            >,
                            stabby::abi::Union<
                                stabby::abi::Union<
                                    stabby::abi::Union<(), Str<'static>>,
                                    Str<'static>,
                                >,
                                u32,
                            >,
                        >,
                    >,
                    stabby::abi::StableIf<
                        stabby::abi::StableLike<
                            for<'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                            ) -> u32,
                            &'static (),
                        >,
                        u32,
                    >,
                >,
                stabby::abi::StableIf<
                    stabby::abi::StableLike<
                        for<'stabby_receiver_lt> extern "C" fn(
                            stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_vt_lt (),
                            >,
                            u32,
                        ),
                        &'static (),
                    >,
                    stabby::abi::Union<(), u32>,
                >,
            >,
        > as stabby::abi::IStable>::Size;
        type Align = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<
                        stabby::abi::FieldPair<
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                    ) -> !,
                                    &'static (),
                                >,
                                (),
                            >,
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt, 'a> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                        Str<'a>,
                                        Str<'a>,
                                        Str<'a>,
                                    ) -> !,
                                    &'static (),
                                >,
                                stabby::abi::Union<
                                    stabby::abi::Union<
                                        stabby::abi::Union<(), Str<'static>>,
                                        Str<'static>,
                                    >,
                                    Str<'static>,
                                >,
                            >,
                        >,
                        stabby::abi::StableIf<
                            stabby::abi::StableLike<
                                for<'stabby_receiver_lt, 'a> extern "C" fn(
                                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                    ::core::marker::PhantomData<
                                        &'stabby_receiver_lt &'stabby_vt_lt (),
                                    >,
                                    Str<'a>,
                                    Str<'a>,
                                    u32,
                                ) -> !,
                                &'static (),
                            >,
                            stabby::abi::Union<
                                stabby::abi::Union<
                                    stabby::abi::Union<(), Str<'static>>,
                                    Str<'static>,
                                >,
                                u32,
                            >,
                        >,
                    >,
                    stabby::abi::StableIf<
                        stabby::abi::StableLike<
                            for<'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                            ) -> u32,
                            &'static (),
                        >,
                        u32,
                    >,
                >,
                stabby::abi::StableIf<
                    stabby::abi::StableLike<
                        for<'stabby_receiver_lt> extern "C" fn(
                            stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_vt_lt (),
                            >,
                            u32,
                        ),
                        &'static (),
                    >,
                    stabby::abi::Union<(), u32>,
                >,
            >,
        > as stabby::abi::IStable>::Align;
        type HasExactlyOneNiche = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<
                        stabby::abi::FieldPair<
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                    ) -> !,
                                    &'static (),
                                >,
                                (),
                            >,
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt, 'a> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                        Str<'a>,
                                        Str<'a>,
                                        Str<'a>,
                                    ) -> !,
                                    &'static (),
                                >,
                                stabby::abi::Union<
                                    stabby::abi::Union<
                                        stabby::abi::Union<(), Str<'static>>,
                                        Str<'static>,
                                    >,
                                    Str<'static>,
                                >,
                            >,
                        >,
                        stabby::abi::StableIf<
                            stabby::abi::StableLike<
                                for<'stabby_receiver_lt, 'a> extern "C" fn(
                                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                    ::core::marker::PhantomData<
                                        &'stabby_receiver_lt &'stabby_vt_lt (),
                                    >,
                                    Str<'a>,
                                    Str<'a>,
                                    u32,
                                ) -> !,
                                &'static (),
                            >,
                            stabby::abi::Union<
                                stabby::abi::Union<
                                    stabby::abi::Union<(), Str<'static>>,
                                    Str<'static>,
                                >,
                                u32,
                            >,
                        >,
                    >,
                    stabby::abi::StableIf<
                        stabby::abi::StableLike<
                            for<'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                            ) -> u32,
                            &'static (),
                        >,
                        u32,
                    >,
                >,
                stabby::abi::StableIf<
                    stabby::abi::StableLike<
                        for<'stabby_receiver_lt> extern "C" fn(
                            stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_vt_lt (),
                            >,
                            u32,
                        ),
                        &'static (),
                    >,
                    stabby::abi::Union<(), u32>,
                >,
            >,
        > as stabby::abi::IStable>::HasExactlyOneNiche;
        type ContainsIndirections = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<
                        stabby::abi::FieldPair<
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                    ) -> !,
                                    &'static (),
                                >,
                                (),
                            >,
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt, 'a> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                        Str<'a>,
                                        Str<'a>,
                                        Str<'a>,
                                    ) -> !,
                                    &'static (),
                                >,
                                stabby::abi::Union<
                                    stabby::abi::Union<
                                        stabby::abi::Union<(), Str<'static>>,
                                        Str<'static>,
                                    >,
                                    Str<'static>,
                                >,
                            >,
                        >,
                        stabby::abi::StableIf<
                            stabby::abi::StableLike<
                                for<'stabby_receiver_lt, 'a> extern "C" fn(
                                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                    ::core::marker::PhantomData<
                                        &'stabby_receiver_lt &'stabby_vt_lt (),
                                    >,
                                    Str<'a>,
                                    Str<'a>,
                                    u32,
                                ) -> !,
                                &'static (),
                            >,
                            stabby::abi::Union<
                                stabby::abi::Union<
                                    stabby::abi::Union<(), Str<'static>>,
                                    Str<'static>,
                                >,
                                u32,
                            >,
                        >,
                    >,
                    stabby::abi::StableIf<
                        stabby::abi::StableLike<
                            for<'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                            ) -> u32,
                            &'static (),
                        >,
                        u32,
                    >,
                >,
                stabby::abi::StableIf<
                    stabby::abi::StableLike<
                        for<'stabby_receiver_lt> extern "C" fn(
                            stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_vt_lt (),
                            >,
                            u32,
                        ),
                        &'static (),
                    >,
                    stabby::abi::Union<(), u32>,
                >,
            >,
        > as stabby::abi::IStable>::ContainsIndirections;
        const REPORT: &'static stabby::abi::report::TypeReport = &stabby::abi::report::TypeReport {
            name: stabby::abi::str::Str::new("StabbyVtableTrezorApiV1"),
            module: stabby::abi::str::Str::new("trezor_app_sdk::traits::trezor_v1"),
            fields: unsafe {
                stabby::abi::StableLike::new(
                    Some(
                        &stabby::abi::report::FieldReport {
                            name: stabby::abi::str::Str::new("sleep"),
                            ty: <stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                        u32,
                                    ),
                                    &'static (),
                                >,
                                stabby::abi::Union<(), u32>,
                            > as stabby::abi::IStable>::REPORT,
                            next_field: stabby::abi::StableLike::new(
                                Some(
                                    &stabby::abi::report::FieldReport {
                                        name: stabby::abi::str::Str::new("systick_ms"),
                                        ty: <stabby::abi::StableIf<
                                            stabby::abi::StableLike<
                                                for<'stabby_receiver_lt> extern "C" fn(
                                                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                                    ::core::marker::PhantomData<
                                                        &'stabby_receiver_lt &'stabby_vt_lt (),
                                                    >,
                                                ) -> u32,
                                                &'static (),
                                            >,
                                            u32,
                                        > as stabby::abi::IStable>::REPORT,
                                        next_field: stabby::abi::StableLike::new(
                                            Some(
                                                &stabby::abi::report::FieldReport {
                                                    name: stabby::abi::str::Str::new("system_exit_fatal"),
                                                    ty: <stabby::abi::StableIf<
                                                        stabby::abi::StableLike<
                                                            for<'stabby_receiver_lt, 'a> extern "C" fn(
                                                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                                                ::core::marker::PhantomData<
                                                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                                                >,
                                                                Str<'a>,
                                                                Str<'a>,
                                                                u32,
                                                            ) -> !,
                                                            &'static (),
                                                        >,
                                                        stabby::abi::Union<
                                                            stabby::abi::Union<
                                                                stabby::abi::Union<(), Str<'static>>,
                                                                Str<'static>,
                                                            >,
                                                            u32,
                                                        >,
                                                    > as stabby::abi::IStable>::REPORT,
                                                    next_field: stabby::abi::StableLike::new(
                                                        Some(
                                                            &stabby::abi::report::FieldReport {
                                                                name: stabby::abi::str::Str::new("system_exit_error"),
                                                                ty: <stabby::abi::StableIf<
                                                                    stabby::abi::StableLike<
                                                                        for<'stabby_receiver_lt, 'a> extern "C" fn(
                                                                            stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                                                            ::core::marker::PhantomData<
                                                                                &'stabby_receiver_lt &'stabby_vt_lt (),
                                                                            >,
                                                                            Str<'a>,
                                                                            Str<'a>,
                                                                            Str<'a>,
                                                                        ) -> !,
                                                                        &'static (),
                                                                    >,
                                                                    stabby::abi::Union<
                                                                        stabby::abi::Union<
                                                                            stabby::abi::Union<(), Str<'static>>,
                                                                            Str<'static>,
                                                                        >,
                                                                        Str<'static>,
                                                                    >,
                                                                > as stabby::abi::IStable>::REPORT,
                                                                next_field: stabby::abi::StableLike::new(
                                                                    Some(
                                                                        &stabby::abi::report::FieldReport {
                                                                            name: stabby::abi::str::Str::new("system_exit"),
                                                                            ty: <stabby::abi::StableIf<
                                                                                stabby::abi::StableLike<
                                                                                    for<'stabby_receiver_lt> extern "C" fn(
                                                                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                                                                        ::core::marker::PhantomData<
                                                                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                                                                        >,
                                                                                    ) -> !,
                                                                                    &'static (),
                                                                                >,
                                                                                (),
                                                                            > as stabby::abi::IStable>::REPORT,
                                                                            next_field: stabby::abi::StableLike::new(None),
                                                                        },
                                                                    ),
                                                                ),
                                                            },
                                                        ),
                                                    ),
                                                },
                                            ),
                                        ),
                                    },
                                ),
                            ),
                        },
                    ),
                )
            },
            version: 0u32,
            tyty: stabby::abi::report::TyTy::Struct,
        };
        const ID: u64 = {
            if core::mem::size_of::<Self>()
                != <<Self as stabby::abi::IStable>::Size as stabby::abi::Unsigned>::USIZE
            {
                {
                    ::core::panicking::panic_fmt(
                        format_args!(
                            "StabbyVtableTrezorApiV1\'s size was mis-evaluated by stabby, this is definitely a bug and may cause UB, please file an issue",
                        ),
                    );
                }
            }
            if core::mem::align_of::<Self>()
                != <<Self as stabby::abi::IStable>::Align as stabby::abi::Unsigned>::USIZE
            {
                {
                    ::core::panicking::panic_fmt(
                        format_args!(
                            "StabbyVtableTrezorApiV1\'s align was mis-evaluated by stabby, this is definitely a bug and may cause UB, please file an issue",
                        ),
                    );
                }
            }
            stabby::abi::report::gen_id(Self::REPORT)
        };
    }
    #[allow(dead_code, missing_docs)]
    struct OptimizedLayoutForStabbyVtableTrezorApiV1<'stabby_vt_lt> {
        ///An stabby-generated item for [`TrezorApiV1`]
        pub system_exit: stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                ) -> !,
                &'static (),
            >,
            (),
        >,
        ///An stabby-generated item for [`TrezorApiV1`]
        pub system_exit_error: stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt, 'a> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    Str<'a>,
                    Str<'a>,
                    Str<'a>,
                ) -> !,
                &'static (),
            >,
            stabby::abi::Union<
                stabby::abi::Union<stabby::abi::Union<(), Str<'static>>, Str<'static>>,
                Str<'static>,
            >,
        >,
        ///An stabby-generated item for [`TrezorApiV1`]
        pub system_exit_fatal: stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt, 'a> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    Str<'a>,
                    Str<'a>,
                    u32,
                ) -> !,
                &'static (),
            >,
            stabby::abi::Union<
                stabby::abi::Union<stabby::abi::Union<(), Str<'static>>, Str<'static>>,
                u32,
            >,
        >,
        ///An stabby-generated item for [`TrezorApiV1`]
        pub systick_ms: stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                ) -> u32,
                &'static (),
            >,
            u32,
        >,
        ///An stabby-generated item for [`TrezorApiV1`]
        pub sleep: stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    u32,
                ),
                &'static (),
            >,
            stabby::abi::Union<(), u32>,
        >,
    }
    impl<'stabby_vt_lt> StabbyVtableTrezorApiV1<'stabby_vt_lt>
    where
        stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<
                        stabby::abi::FieldPair<
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                    ) -> !,
                                    &'static (),
                                >,
                                (),
                            >,
                            stabby::abi::StableIf<
                                stabby::abi::StableLike<
                                    for<'stabby_receiver_lt, 'a> extern "C" fn(
                                        stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                        ::core::marker::PhantomData<
                                            &'stabby_receiver_lt &'stabby_vt_lt (),
                                        >,
                                        Str<'a>,
                                        Str<'a>,
                                        Str<'a>,
                                    ) -> !,
                                    &'static (),
                                >,
                                stabby::abi::Union<
                                    stabby::abi::Union<
                                        stabby::abi::Union<(), Str<'static>>,
                                        Str<'static>,
                                    >,
                                    Str<'static>,
                                >,
                            >,
                        >,
                        stabby::abi::StableIf<
                            stabby::abi::StableLike<
                                for<'stabby_receiver_lt, 'a> extern "C" fn(
                                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                    ::core::marker::PhantomData<
                                        &'stabby_receiver_lt &'stabby_vt_lt (),
                                    >,
                                    Str<'a>,
                                    Str<'a>,
                                    u32,
                                ) -> !,
                                &'static (),
                            >,
                            stabby::abi::Union<
                                stabby::abi::Union<
                                    stabby::abi::Union<(), Str<'static>>,
                                    Str<'static>,
                                >,
                                u32,
                            >,
                        >,
                    >,
                    stabby::abi::StableIf<
                        stabby::abi::StableLike<
                            for<'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                            ) -> u32,
                            &'static (),
                        >,
                        u32,
                    >,
                >,
                stabby::abi::StableIf<
                    stabby::abi::StableLike<
                        for<'stabby_receiver_lt> extern "C" fn(
                            stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_vt_lt (),
                            >,
                            u32,
                        ),
                        &'static (),
                    >,
                    stabby::abi::Union<(), u32>,
                >,
            >,
        >: stabby::abi::IStable,
        stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    u32,
                ),
                &'static (),
            >,
            stabby::abi::Union<(), u32>,
        >: stabby::abi::IStable,
        stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                ) -> u32,
                &'static (),
            >,
            u32,
        >: stabby::abi::IStable,
        stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt, 'a> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    Str<'a>,
                    Str<'a>,
                    u32,
                ) -> !,
                &'static (),
            >,
            stabby::abi::Union<
                stabby::abi::Union<stabby::abi::Union<(), Str<'static>>, Str<'static>>,
                u32,
            >,
        >: stabby::abi::IStable,
        stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt, 'a> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                    Str<'a>,
                    Str<'a>,
                    Str<'a>,
                ) -> !,
                &'static (),
            >,
            stabby::abi::Union<
                stabby::abi::Union<stabby::abi::Union<(), Str<'static>>, Str<'static>>,
                Str<'static>,
            >,
        >: stabby::abi::IStable,
        stabby::abi::StableIf<
            stabby::abi::StableLike<
                for<'stabby_receiver_lt> extern "C" fn(
                    stabby::abi::AnonymRef<'stabby_receiver_lt>,
                    ::core::marker::PhantomData<&'stabby_receiver_lt &'stabby_vt_lt ()>,
                ) -> !,
                &'static (),
            >,
            (),
        >: stabby::abi::IStable,
    {
        ///Returns true if the layout for [`StabbyVtableTrezorApiV1`] is smaller or equal to that Rust would have generated for it.
        pub const fn has_optimal_layout() -> bool {
            core::mem::size_of::<Self>()
                <= core::mem::size_of::<
                    OptimizedLayoutForStabbyVtableTrezorApiV1<'stabby_vt_lt>,
                >()
        }
    }
    impl<'stabby_vt_lt> Clone for StabbyVtableTrezorApiV1<'stabby_vt_lt> {
        fn clone(&self) -> Self {
            *self
        }
    }
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    impl<'stabby_vt_lt> Copy for StabbyVtableTrezorApiV1<'stabby_vt_lt> {}
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    impl<'stabby_vt_lt> core::cmp::PartialEq for StabbyVtableTrezorApiV1<'stabby_vt_lt> {
        fn eq(&self, other: &Self) -> bool {
            core::ptr::eq(
                (*unsafe { self.system_exit.as_ref_unchecked() }) as *const (),
                (*unsafe { other.system_exit.as_ref_unchecked() }) as *const _,
            )
                && core::ptr::eq(
                    (*unsafe { self.system_exit_error.as_ref_unchecked() }) as *const (),
                    (*unsafe { other.system_exit_error.as_ref_unchecked() }) as *const _,
                )
                && core::ptr::eq(
                    (*unsafe { self.system_exit_fatal.as_ref_unchecked() }) as *const (),
                    (*unsafe { other.system_exit_fatal.as_ref_unchecked() }) as *const _,
                )
                && core::ptr::eq(
                    (*unsafe { self.systick_ms.as_ref_unchecked() }) as *const (),
                    (*unsafe { other.systick_ms.as_ref_unchecked() }) as *const _,
                )
                && core::ptr::eq(
                    (*unsafe { self.sleep.as_ref_unchecked() }) as *const (),
                    (*unsafe { other.sleep.as_ref_unchecked() }) as *const _,
                ) && true
        }
    }
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    impl<'stabby_vt_lt> core::hash::Hash for StabbyVtableTrezorApiV1<'stabby_vt_lt> {
        fn hash<H: core::hash::Hasher>(&self, state: &mut H) {
            self.system_exit.hash(state);
            self.system_exit_error.hash(state);
            self.system_exit_fatal.hash(state);
            self.systick_ms.hash(state);
            self.sleep.hash(state);
        }
    }
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    impl<'stabby_vt_lt> core::fmt::Debug for StabbyVtableTrezorApiV1<'stabby_vt_lt> {
        fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
            let mut s = f.debug_struct("StabbyVtableTrezorApiV1");
            s.field(
                "system_exit",
                &format_args!("{0:p}", unsafe { self.system_exit.as_ref_unchecked() }),
            );
            s.field(
                "system_exit_error",
                &format_args!(
                    "{0:p}",
                    unsafe { self.system_exit_error.as_ref_unchecked() },
                ),
            );
            s.field(
                "system_exit_fatal",
                &format_args!(
                    "{0:p}",
                    unsafe { self.system_exit_fatal.as_ref_unchecked() },
                ),
            );
            s.field(
                "systick_ms",
                &format_args!("{0:p}", unsafe { self.systick_ms.as_ref_unchecked() }),
            );
            s.field(
                "sleep",
                &format_args!("{0:p}", unsafe { self.sleep.as_ref_unchecked() }),
            );
            s.finish()
        }
    }
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    impl<
        'stabby_vt_lt,
        StabbyArbitraryType,
    > stabby::abi::vtable::IConstConstructor<'stabby_vt_lt, StabbyArbitraryType>
    for StabbyVtableTrezorApiV1<'stabby_vt_lt>
    where
        StabbyArbitraryType: TrezorApiV1,
    {
        #[allow(clippy::incompatible_msrv)]
        const VTABLE: StabbyVtableTrezorApiV1<'stabby_vt_lt> = StabbyVtableTrezorApiV1 {
            system_exit: unsafe {
                stabby::abi::StableIf::new(
                    stabby::abi::StableLike::new({
                        extern "C" fn ext_system_exit<
                            'stabby_local_lt,
                            'stabby_receiver_lt,
                            StabbyArbitraryType: 'stabby_local_lt,
                        >(
                            this: stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            _lt_proof: ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_local_lt (),
                            >,
                        ) -> !
                        where
                            StabbyArbitraryType: TrezorApiV1,
                        {
                            unsafe {
                                <StabbyArbitraryType as TrezorApiV1>::system_exit(
                                    this.cast::<StabbyArbitraryType>().as_ref(),
                                )
                            }
                        }
                        ext_system_exit::<StabbyArbitraryType>
                            as for<'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                            ) -> !
                    }),
                )
            },
            system_exit_error: unsafe {
                stabby::abi::StableIf::new(
                    stabby::abi::StableLike::new({
                        extern "C" fn ext_system_exit_error<
                            'stabby_local_lt,
                            'a,
                            'stabby_receiver_lt,
                            StabbyArbitraryType: 'stabby_local_lt,
                        >(
                            this: stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            _lt_proof: ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_local_lt (),
                            >,
                            _0: Str<'a>,
                            _1: Str<'a>,
                            _2: Str<'a>,
                        ) -> !
                        where
                            StabbyArbitraryType: TrezorApiV1,
                        {
                            unsafe {
                                <StabbyArbitraryType as TrezorApiV1>::system_exit_error(
                                    this.cast::<StabbyArbitraryType>().as_ref(),
                                    _0,
                                    _1,
                                    _2,
                                )
                            }
                        }
                        ext_system_exit_error::<StabbyArbitraryType>
                            as for<'a, 'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                                Str<'a>,
                                Str<'a>,
                                Str<'a>,
                            ) -> !
                    }),
                )
            },
            system_exit_fatal: unsafe {
                stabby::abi::StableIf::new(
                    stabby::abi::StableLike::new({
                        extern "C" fn ext_system_exit_fatal<
                            'stabby_local_lt,
                            'a,
                            'stabby_receiver_lt,
                            StabbyArbitraryType: 'stabby_local_lt,
                        >(
                            this: stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            _lt_proof: ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_local_lt (),
                            >,
                            _0: Str<'a>,
                            _1: Str<'a>,
                            _2: u32,
                        ) -> !
                        where
                            StabbyArbitraryType: TrezorApiV1,
                        {
                            unsafe {
                                <StabbyArbitraryType as TrezorApiV1>::system_exit_fatal(
                                    this.cast::<StabbyArbitraryType>().as_ref(),
                                    _0,
                                    _1,
                                    _2,
                                )
                            }
                        }
                        ext_system_exit_fatal::<StabbyArbitraryType>
                            as for<'a, 'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                                Str<'a>,
                                Str<'a>,
                                u32,
                            ) -> !
                    }),
                )
            },
            systick_ms: unsafe {
                stabby::abi::StableIf::new(
                    stabby::abi::StableLike::new({
                        extern "C" fn ext_systick_ms<
                            'stabby_local_lt,
                            'stabby_receiver_lt,
                            StabbyArbitraryType: 'stabby_local_lt,
                        >(
                            this: stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            _lt_proof: ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_local_lt (),
                            >,
                        ) -> u32
                        where
                            StabbyArbitraryType: TrezorApiV1,
                        {
                            unsafe {
                                <StabbyArbitraryType as TrezorApiV1>::systick_ms(
                                    this.cast::<StabbyArbitraryType>().as_ref(),
                                )
                            }
                        }
                        ext_systick_ms::<StabbyArbitraryType>
                            as for<'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                            ) -> u32
                    }),
                )
            },
            sleep: unsafe {
                stabby::abi::StableIf::new(
                    stabby::abi::StableLike::new({
                        extern "C" fn ext_sleep<
                            'stabby_local_lt,
                            'stabby_receiver_lt,
                            StabbyArbitraryType: 'stabby_local_lt,
                        >(
                            this: stabby::abi::AnonymRef<'stabby_receiver_lt>,
                            _lt_proof: ::core::marker::PhantomData<
                                &'stabby_receiver_lt &'stabby_local_lt (),
                            >,
                            _0: u32,
                        )
                        where
                            StabbyArbitraryType: TrezorApiV1,
                        {
                            unsafe {
                                <StabbyArbitraryType as TrezorApiV1>::sleep(
                                    this.cast::<StabbyArbitraryType>().as_ref(),
                                    _0,
                                )
                            }
                        }
                        ext_sleep::<StabbyArbitraryType>
                            as for<'stabby_receiver_lt> extern "C" fn(
                                stabby::abi::AnonymRef<'stabby_receiver_lt>,
                                ::core::marker::PhantomData<
                                    &'stabby_receiver_lt &'stabby_vt_lt (),
                                >,
                                u32,
                            )
                    }),
                )
            },
        };
    }
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    impl<'stabby_vt_lt> stabby::abi::vtable::CompoundVt<'stabby_vt_lt>
    for dyn TrezorApiV1 {
        ///An stabby-generated item for [`TrezorApiV1`]
        type Vt<StabbyNextVtable> = stabby::abi::vtable::VTable<
            StabbyVtableTrezorApiV1<'stabby_vt_lt>,
            StabbyNextVtable,
        >;
    }
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    ///An stabby-generated item for [`TrezorApiV1`]
    pub trait TrezorApiV1Dyn<StabbyTransitiveDerefN> {
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn system_exit(&self) -> !;
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn system_exit_error<'a>(
            &self,
            _0: Str<'a>,
            _1: Str<'a>,
            _2: Str<'a>,
        ) -> !;
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn system_exit_fatal<'a>(
            &self,
            _0: Str<'a>,
            _1: Str<'a>,
            _2: u32,
        ) -> !;
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn systick_ms(&self) -> u32;
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn sleep(&self, _0: u32);
    }
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    impl<
        'stabby_vt_lt,
        StabbyVtProvider: stabby::abi::vtable::TransitiveDeref<
                StabbyVtableTrezorApiV1<'stabby_vt_lt>,
                StabbyTransitiveDerefN,
            > + Copy,
        StabbyTransitiveDerefN,
    > TrezorApiV1Dyn<StabbyTransitiveDerefN>
    for stabby::abi::DynRef<'_, StabbyVtProvider> {
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn system_exit(&self) -> ! {
            unsafe {
                (self
                    .vtable()
                    .tderef()
                    .system_exit
                    .as_ref_unchecked())(self.ptr(), ::core::marker::PhantomData)
            }
        }
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn system_exit_error<'a>(
            &self,
            _0: Str<'a>,
            _1: Str<'a>,
            _2: Str<'a>,
        ) -> ! {
            unsafe {
                (self
                    .vtable()
                    .tderef()
                    .system_exit_error
                    .as_ref_unchecked())(
                    self.ptr(),
                    ::core::marker::PhantomData,
                    _0,
                    _1,
                    _2,
                )
            }
        }
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn system_exit_fatal<'a>(
            &self,
            _0: Str<'a>,
            _1: Str<'a>,
            _2: u32,
        ) -> ! {
            unsafe {
                (self
                    .vtable()
                    .tderef()
                    .system_exit_fatal
                    .as_ref_unchecked())(
                    self.ptr(),
                    ::core::marker::PhantomData,
                    _0,
                    _1,
                    _2,
                )
            }
        }
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn systick_ms(&self) -> u32 {
            unsafe {
                (self
                    .vtable()
                    .tderef()
                    .systick_ms
                    .as_ref_unchecked())(self.ptr(), ::core::marker::PhantomData)
            }
        }
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn sleep(&self, _0: u32) {
            unsafe {
                (self
                    .vtable()
                    .tderef()
                    .sleep
                    .as_ref_unchecked())(self.ptr(), ::core::marker::PhantomData, _0)
            }
        }
    }
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    impl<
        'stabby_vt_lt,
        StabbyPtrProvider: stabby::abi::IPtrOwned + stabby::abi::IPtr,
        StabbyVtProvider: stabby::abi::vtable::HasDropVt + Copy
            + stabby::abi::vtable::TransitiveDeref<
                StabbyVtableTrezorApiV1<'stabby_vt_lt>,
                StabbyTransitiveDerefN,
            >,
        StabbyTransitiveDerefN,
    > TrezorApiV1Dyn<StabbyTransitiveDerefN>
    for stabby::abi::Dyn<'_, StabbyPtrProvider, StabbyVtProvider> {
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn system_exit(&self) -> ! {
            unsafe {
                (self
                    .vtable()
                    .tderef()
                    .system_exit
                    .as_ref_unchecked())(
                    self.ptr().as_ref(),
                    ::core::marker::PhantomData,
                )
            }
        }
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn system_exit_error<'a>(
            &self,
            _0: Str<'a>,
            _1: Str<'a>,
            _2: Str<'a>,
        ) -> ! {
            unsafe {
                (self
                    .vtable()
                    .tderef()
                    .system_exit_error
                    .as_ref_unchecked())(
                    self.ptr().as_ref(),
                    ::core::marker::PhantomData,
                    _0,
                    _1,
                    _2,
                )
            }
        }
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn system_exit_fatal<'a>(
            &self,
            _0: Str<'a>,
            _1: Str<'a>,
            _2: u32,
        ) -> ! {
            unsafe {
                (self
                    .vtable()
                    .tderef()
                    .system_exit_fatal
                    .as_ref_unchecked())(
                    self.ptr().as_ref(),
                    ::core::marker::PhantomData,
                    _0,
                    _1,
                    _2,
                )
            }
        }
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn systick_ms(&self) -> u32 {
            unsafe {
                (self
                    .vtable()
                    .tderef()
                    .systick_ms
                    .as_ref_unchecked())(
                    self.ptr().as_ref(),
                    ::core::marker::PhantomData,
                )
            }
        }
        ///An stabby-generated item for [`TrezorApiV1`]
        extern "C" fn sleep(&self, _0: u32) {
            unsafe {
                (self
                    .vtable()
                    .tderef()
                    .sleep
                    .as_ref_unchecked())(
                    self.ptr().as_ref(),
                    ::core::marker::PhantomData,
                    _0,
                )
            }
        }
    }
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    ///An stabby-generated item for [`TrezorApiV1`]
    pub trait TrezorApiV1DynMut<
        StabbyTransitiveDerefN,
    >: TrezorApiV1Dyn<StabbyTransitiveDerefN> {}
    #[allow(unknown_lints)]
    #[allow(clippy::multiple_bound_locations)]
    impl<
        'stabby_vt_lt,
        StabbyPtrProvider,
        StabbyVtProvider,
        StabbyTransitiveDerefN,
    > TrezorApiV1DynMut<StabbyTransitiveDerefN>
    for stabby::abi::Dyn<'_, StabbyPtrProvider, StabbyVtProvider>
    where
        StabbyPtrProvider: stabby::abi::IPtrOwned + stabby::abi::IPtrMut,
        StabbyVtProvider: stabby::abi::vtable::HasDropVt + Copy
            + stabby::abi::vtable::TransitiveDeref<
                StabbyVtableTrezorApiV1<'stabby_vt_lt>,
                StabbyTransitiveDerefN,
            >,
    {}
    pub type StaticTrezorApiV1 = stabby::abi::DynRef<
        'static,
        <dyn Sync as stabby::abi::vtable::CompoundVt<
            'static,
        >>::Vt<
            <dyn Send as stabby::abi::vtable::CompoundVt<
                'static,
            >>::Vt<
                <dyn TrezorApiV1 as stabby::abi::vtable::CompoundVt<
                    'static,
                >>::Vt<stabby::abi::vtable::VtDrop>,
            >,
        >,
    >;
    #[repr(C)]
    pub struct TrezorApiV1Struct {
        pub api: StaticTrezorApiV1,
        pub allocator: StaticAllocatorV1,
        pub crypto: StaticCryptoV1,
        pub syslog: StaticSyslogV1,
    }
    #[automatically_derived]
    unsafe impl stabby::abi::IStable for TrezorApiV1Struct
    where
        stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<StaticTrezorApiV1, StaticAllocatorV1>,
                    StaticCryptoV1,
                >,
                StaticSyslogV1,
            >,
        >: stabby::abi::IStable,
        StaticSyslogV1: stabby::abi::IStable,
        StaticCryptoV1: stabby::abi::IStable,
        StaticAllocatorV1: stabby::abi::IStable,
        StaticTrezorApiV1: stabby::abi::IStable,
    {
        type ForbiddenValues = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<StaticTrezorApiV1, StaticAllocatorV1>,
                    StaticCryptoV1,
                >,
                StaticSyslogV1,
            >,
        > as stabby::abi::IStable>::ForbiddenValues;
        type UnusedBits = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<StaticTrezorApiV1, StaticAllocatorV1>,
                    StaticCryptoV1,
                >,
                StaticSyslogV1,
            >,
        > as stabby::abi::IStable>::UnusedBits;
        type Size = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<StaticTrezorApiV1, StaticAllocatorV1>,
                    StaticCryptoV1,
                >,
                StaticSyslogV1,
            >,
        > as stabby::abi::IStable>::Size;
        type Align = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<StaticTrezorApiV1, StaticAllocatorV1>,
                    StaticCryptoV1,
                >,
                StaticSyslogV1,
            >,
        > as stabby::abi::IStable>::Align;
        type HasExactlyOneNiche = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<StaticTrezorApiV1, StaticAllocatorV1>,
                    StaticCryptoV1,
                >,
                StaticSyslogV1,
            >,
        > as stabby::abi::IStable>::HasExactlyOneNiche;
        type ContainsIndirections = <stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<StaticTrezorApiV1, StaticAllocatorV1>,
                    StaticCryptoV1,
                >,
                StaticSyslogV1,
            >,
        > as stabby::abi::IStable>::ContainsIndirections;
        const REPORT: &'static stabby::abi::report::TypeReport = &stabby::abi::report::TypeReport {
            name: stabby::abi::str::Str::new("TrezorApiV1Struct"),
            module: stabby::abi::str::Str::new("trezor_app_sdk::traits::trezor_v1"),
            fields: unsafe {
                stabby::abi::StableLike::new(
                    Some(
                        &stabby::abi::report::FieldReport {
                            name: stabby::abi::str::Str::new("syslog"),
                            ty: <StaticSyslogV1 as stabby::abi::IStable>::REPORT,
                            next_field: stabby::abi::StableLike::new(
                                Some(
                                    &stabby::abi::report::FieldReport {
                                        name: stabby::abi::str::Str::new("crypto"),
                                        ty: <StaticCryptoV1 as stabby::abi::IStable>::REPORT,
                                        next_field: stabby::abi::StableLike::new(
                                            Some(
                                                &stabby::abi::report::FieldReport {
                                                    name: stabby::abi::str::Str::new("allocator"),
                                                    ty: <StaticAllocatorV1 as stabby::abi::IStable>::REPORT,
                                                    next_field: stabby::abi::StableLike::new(
                                                        Some(
                                                            &stabby::abi::report::FieldReport {
                                                                name: stabby::abi::str::Str::new("api"),
                                                                ty: <StaticTrezorApiV1 as stabby::abi::IStable>::REPORT,
                                                                next_field: stabby::abi::StableLike::new(None),
                                                            },
                                                        ),
                                                    ),
                                                },
                                            ),
                                        ),
                                    },
                                ),
                            ),
                        },
                    ),
                )
            },
            version: 0u32,
            tyty: stabby::abi::report::TyTy::Struct,
        };
        const ID: u64 = {
            if core::mem::size_of::<Self>()
                != <<Self as stabby::abi::IStable>::Size as stabby::abi::Unsigned>::USIZE
            {
                {
                    ::core::panicking::panic_fmt(
                        format_args!(
                            "TrezorApiV1Struct\'s size was mis-evaluated by stabby, this is definitely a bug and may cause UB, please file an issue",
                        ),
                    );
                }
            }
            if core::mem::align_of::<Self>()
                != <<Self as stabby::abi::IStable>::Align as stabby::abi::Unsigned>::USIZE
            {
                {
                    ::core::panicking::panic_fmt(
                        format_args!(
                            "TrezorApiV1Struct\'s align was mis-evaluated by stabby, this is definitely a bug and may cause UB, please file an issue",
                        ),
                    );
                }
            }
            stabby::abi::report::gen_id(Self::REPORT)
        };
    }
    #[allow(dead_code, missing_docs)]
    struct OptimizedLayoutForTrezorApiV1Struct {
        pub api: StaticTrezorApiV1,
        pub allocator: StaticAllocatorV1,
        pub crypto: StaticCryptoV1,
        pub syslog: StaticSyslogV1,
    }
    const _: () = {
        if !<TrezorApiV1Struct>::has_optimal_layout() {
            {
                ::core::panicking::panic_fmt(
                    format_args!(
                        "TrezorApiV1Struct\'s layout is sub-optimal, reorder fields or use `#[stabby::stabby(no_opt)]`",
                    ),
                );
            }
        }
    };
    impl TrezorApiV1Struct
    where
        stabby::abi::Struct<
            stabby::abi::FieldPair<
                stabby::abi::FieldPair<
                    stabby::abi::FieldPair<StaticTrezorApiV1, StaticAllocatorV1>,
                    StaticCryptoV1,
                >,
                StaticSyslogV1,
            >,
        >: stabby::abi::IStable,
        StaticSyslogV1: stabby::abi::IStable,
        StaticCryptoV1: stabby::abi::IStable,
        StaticAllocatorV1: stabby::abi::IStable,
        StaticTrezorApiV1: stabby::abi::IStable,
    {
        ///Returns true if the layout for [`TrezorApiV1Struct`] is smaller or equal to that Rust would have generated for it.
        pub const fn has_optimal_layout() -> bool {
            core::mem::size_of::<Self>()
                <= core::mem::size_of::<OptimizedLayoutForTrezorApiV1Struct>()
        }
    }
}
