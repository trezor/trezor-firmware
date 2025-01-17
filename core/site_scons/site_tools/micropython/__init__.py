import SCons.Builder


def generate(env):

    env.SetDefault(
        QSTRCOL="site_scons/site_tools/micropython/qstrdefs.py",
        MODULECOL="site_scons/site_tools/micropython/moduledefs.py",
    )

    env["BUILDERS"]["MicroPyDefines"] = SCons.Builder.Builder(
        action="$CC -E $CCFLAGS_QSTR $CFLAGS $CCFLAGS $_CCCOMCOM $SOURCE > $TARGET",
        suffix=".upydef",
        single_source=True,
    )

    env["BUILDERS"]["CollectQstr"] = SCons.Builder.Builder(
        action="cat $SOURCES | perl -nle 'print \"Q($1)\" while /MP_QSTR_(\\w+)/g' > $TARGET"
    )

    env["BUILDERS"]["PreprocessQstr"] = SCons.Builder.Builder(
        action="cat $SOURCES"
        " | $SED 's/^Q(.*)/\"&\"/'"
        " | $CC -E $CFLAGS $CCFLAGS $_CCCOMCOM -"
        " | $SED 's/^\"\\(Q(.*)\\)\"/\\1/' > $TARGET",
    )

    env["BUILDERS"]["GenerateQstrDefs"] = SCons.Builder.Builder(
        action="$MAKEQSTRDATA $SOURCE > $TARGET",
    )

    env["BUILDERS"]["CollectModules"] = SCons.Builder.Builder(
        action="grep ^MP_REGISTER_MODULE $SOURCES > $TARGET"
        # action="$CC -E $CCFLAGS_QSTR $CFLAGS $CCFLAGS $_CCCOMCOM $SOURCES"
        # " | $PYTHON $MODULECOL > $TARGET"
    )

    def generate_frozen_module(source, target, env, for_signature):
        target = str(target[0])
        source = str(source[0])
        source_name = source.replace(env["source_dir"], "")
        # replace "utils.BITCOIN_ONLY" with literal constant (True/False)
        # so the compiler can optimize out the things we don't want
        btc_only = env["bitcoin_only"] == "1"
        backlight = env["backlight"]
        optiga = env["optiga"]
        touch = env["use_touch"]
        button = env["use_button"]
        layout_bolt = env["ui_layout"] == "UI_LAYOUT_BOLT"
        layout_caesar = env["ui_layout"] == "UI_LAYOUT_CAESAR"
        layout_delizia = env["ui_layout"] == "UI_LAYOUT_DELIZIA"
        thp = env["thp"]
        interim = f"{target[:-4]}.i"  # replace .mpy with .i
        sed_scripts = [
            rf"-e 's/utils\.BITCOIN_ONLY/{btc_only}/g'",
            rf"-e 's/utils\.USE_BACKLIGHT/{backlight}/g'",
            rf"-e 's/utils\.USE_OPTIGA/{optiga}/g'",
            rf"-e 's/utils\.UI_LAYOUT == \"BOLT\"/{layout_bolt}/g'",
            rf"-e 's/utils\.UI_LAYOUT == \"CAESAR\"/{layout_caesar}/g'",
            rf"-e 's/utils\.UI_LAYOUT == \"DELIZIA\"/{layout_delizia}/g'",
            rf"-e 's/utils\.USE_BUTTON/{button}/g'",
            rf"-e 's/utils\.USE_TOUCH/{touch}/g'",
            rf"-e 's/utils\.USE_THP/{thp}/g'",
            r"-e 's/if TYPE_CHECKING/if False/'",
            r"-e 's/import typing/# \0/'",
            r"-e '/from typing import (/,/^\s*)/ {s/^/# /; }'",
            r"-e 's/from typing import/# \0/'",
        ]

        MODELS = ["T2T1", "T2B1", "T3T1", "T3B1", "T3W1"]

        for internal_model in MODELS:
            model_matches = env["TREZOR_MODEL"] == internal_model
            sed_scripts.extend(
                (
                    rf"-e 's/utils\.INTERNAL_MODEL == \"{internal_model}\"/{model_matches}/g'",
                    rf"-e 's/utils\.INTERNAL_MODEL != \"{internal_model}\"/{not model_matches}/g'",
                )
            )

        return f"$SED {' '.join(sed_scripts)} {source} > {interim} && $MPY_CROSS -o {target} -s {source_name} {interim}"

    env["BUILDERS"]["FrozenModule"] = SCons.Builder.Builder(
        generator=generate_frozen_module,
        suffix=".mpy",
        single_source=True,
    )

    env["BUILDERS"]["FrozenCFile"] = SCons.Builder.Builder(
        action="$MPY_TOOL -f -q $qstr_header $SOURCES > $TARGET",
    )


def exists(env):
    return True
