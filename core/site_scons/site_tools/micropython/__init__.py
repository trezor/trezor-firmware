import SCons.Builder


def generate(env):

    env.SetDefault(
        QSTRCOL='site_scons/site_tools/micropython/qstrdefs.py', )

    env['BUILDERS']['CollectQstr'] = SCons.Builder.Builder(
        action='$CC -E $CCFLAGS_QSTR $CFLAGS $CCFLAGS $_CCCOMCOM $SOURCES'
        ' | $PYTHON $QSTRCOL > $TARGET')

    env['BUILDERS']['PreprocessQstr'] = SCons.Builder.Builder(
        action="cat $SOURCES"
        " | $SED 's/^Q(.*)/\"&\"/'"
        " | $CC -E $CFLAGS $CCFLAGS $_CCCOMCOM -"
        " | $SED 's/^\"\(Q(.*)\)\"/\\1/' > $TARGET", )

    env['BUILDERS']['GenerateQstrDefs'] = SCons.Builder.Builder(
        action='$MAKEQSTRDATA $SOURCE > $TARGET', )

    def generate_frozen_module(source, target, env, for_signature):
        target = str(target[0])
        source = str(source[0])
        source_name = source.replace(env['source_dir'], '')
        return '$MPY_CROSS -o %s -s %s %s' % (target, source_name, source)

    env['BUILDERS']['FrozenModule'] = SCons.Builder.Builder(
        generator=generate_frozen_module,
        suffix='.mpy',
        single_source=True, )

    env['BUILDERS']['FrozenCFile'] = SCons.Builder.Builder(
        action='$MPY_TOOL -f -q $qstr_header $SOURCES > $TARGET', )


def exists(env):
    return True