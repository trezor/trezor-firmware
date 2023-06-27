import SCons.Builder


def generate(env):

    env.SetDefault(
        QSTRCOL='site_scons/site_tools/micropython/qstrdefs.py',
        MODULECOL='site_scons/site_tools/micropython/moduledefs.py', )

    env['BUILDERS']['CollectQstr'] = SCons.Builder.Builder(
        action='$CC -E $CCFLAGS_QSTR $CFLAGS $CCFLAGS $_CCCOMCOM $SOURCES'
        ' | $PYTHON $QSTRCOL > $TARGET')

    env['BUILDERS']['PreprocessQstr'] = SCons.Builder.Builder(
        action="cat $SOURCES"
        " | $SED 's/^Q(.*)/\"&\"/'"
        " | $CC -E $CFLAGS $CCFLAGS $_CCCOMCOM -"
        " | $SED 's/^\"\\(Q(.*)\\)\"/\\1/' > $TARGET", )

    env['BUILDERS']['GenerateQstrDefs'] = SCons.Builder.Builder(
        action='$MAKEQSTRDATA $SOURCE > $TARGET', )

    env['BUILDERS']['CollectModules'] = SCons.Builder.Builder(
        action='$CC -E $CCFLAGS_QSTR $CFLAGS $CCFLAGS $_CCCOMCOM $SOURCES'
        ' | $PYTHON $MODULECOL > $TARGET')

    def generate_frozen_module(source, target, env, for_signature):
        target = str(target[0])
        source = str(source[0])
        source_name = source.replace(env['source_dir'], '')
        # replace "utils.BITCOIN_ONLY" with literal constant (True/False)
        # so the compiler can optimize out the things we don't want
        btc_only = env['bitcoin_only'] == '1'
        backlight = env['backlight']
        interim = f"{target[:-4]}.i"  # replace .mpy with .i
        sed_scripts = " ".join([
            rf"-e 's/utils\.BITCOIN_ONLY/{btc_only}/g'",
            rf"-e 's/utils\.USE_BACKLIGHT/{backlight}/g'",
            r"-e 's/if TYPE_CHECKING/if False/'",
            r"-e 's/import typing/# \0/'",
            r"-e '/from typing import (/,/^\s*)/ {s/^/# /}'",
            r"-e 's/from typing import/# \0/'"
        ])
        return f'$SED {sed_scripts} {source} > {interim} && $MPY_CROSS -o {target} -s {source_name} {interim}'

    env['BUILDERS']['FrozenModule'] = SCons.Builder.Builder(
        generator=generate_frozen_module,
        suffix='.mpy',
        single_source=True, )

    env['BUILDERS']['FrozenCFile'] = SCons.Builder.Builder(
        action='$MPY_TOOL -f -q $qstr_header $SOURCES > $TARGET', )


def exists(env):
    return True
