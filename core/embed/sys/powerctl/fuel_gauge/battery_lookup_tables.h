/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/**
 * Battery SoC Lookup Tables
 * Auto-generated from Python battery characterization script
 */

#ifndef BATTERY_LOOKUP_TABLES_H
#define BATTERY_LOOKUP_TABLES_H

#include <stdint.h>

// Configuration
#define NUM_TEMPERATURE_POINTS 4
#define NUM_SOC_POINTS 100

// Temperature points array (in Celsius)
static const float BATTERY_TEMP_POINTS[NUM_TEMPERATURE_POINTS] = {
    5.30f, 13.02f, 27.24f, 38.15f
};

// Internal resistance array (in ohms) corresponding to each temperature
static const float BATTERY_R_INT[NUM_TEMPERATURE_POINTS] = {
    0.851785f, 0.879662f, 0.607803f, 0.541946f
};

// Total capacity array (in mAh) corresponding to each temperature
static const float BATTERY_CAPACITY[NUM_TEMPERATURE_POINTS] = {
    148.58f, 245.23f, 330.98f, 343.39f
};

// SoC points (constant across all temperature curves)
static const float BATTERY_SOC_POINTS[NUM_SOC_POINTS] = {
    0.000000f, 0.010101f, 0.020202f, 0.030303f, 0.040404f, 0.050505f, 0.060606f, 0.070707f,
    0.080808f, 0.090909f, 0.101010f, 0.111111f, 0.121212f, 0.131313f, 0.141414f, 0.151515f,
    0.161616f, 0.171717f, 0.181818f, 0.191919f, 0.202020f, 0.212121f, 0.222222f, 0.232323f,
    0.242424f, 0.252525f, 0.262626f, 0.272727f, 0.282828f, 0.292929f, 0.303030f, 0.313131f,
    0.323232f, 0.333333f, 0.343434f, 0.353535f, 0.363636f, 0.373737f, 0.383838f, 0.393939f,
    0.404040f, 0.414141f, 0.424242f, 0.434343f, 0.444444f, 0.454545f, 0.464646f, 0.474747f,
    0.484848f, 0.494949f, 0.505051f, 0.515152f, 0.525253f, 0.535354f, 0.545455f, 0.555556f,
    0.565657f, 0.575758f, 0.585859f, 0.595960f, 0.606061f, 0.616162f, 0.626263f, 0.636364f,
    0.646465f, 0.656566f, 0.666667f, 0.676768f, 0.686869f, 0.696970f, 0.707071f, 0.717172f,
    0.727273f, 0.737374f, 0.747475f, 0.757576f, 0.767677f, 0.777778f, 0.787879f, 0.797980f,
    0.808081f, 0.818182f, 0.828283f, 0.838384f, 0.848485f, 0.858586f, 0.868687f, 0.878788f,
    0.888889f, 0.898990f, 0.909091f, 0.919192f, 0.929293f, 0.939394f, 0.949495f, 0.959596f,
    0.969697f, 0.979798f, 0.989899f, 1.000000f
};

// Open circuit voltage arrays for each temperature
static const float BATTERY_VOC_ARRAYS[NUM_TEMPERATURE_POINTS][NUM_SOC_POINTS] = {
    // Temperature: 5.30°C
    {
        3.166033f, 3.174570f, 3.180834f, 3.184543f, 3.185212f, 3.184992f, 3.190821f, 3.197706f,
        3.214448f, 3.215660f, 3.218382f, 3.224444f, 3.225045f, 3.222688f, 3.225184f, 3.227804f,
        3.231713f, 3.236392f, 3.237641f, 3.239050f, 3.242754f, 3.241660f, 3.244952f, 3.243650f,
        3.247836f, 3.250025f, 3.249309f, 3.251065f, 3.253911f, 3.253500f, 3.256131f, 3.258694f,
        3.262777f, 3.266751f, 3.268475f, 3.265963f, 3.265569f, 3.265743f, 3.264746f, 3.267719f,
        3.269099f, 3.275145f, 3.274179f, 3.277729f, 3.277919f, 3.279146f, 3.279419f, 3.281727f,
        3.287394f, 3.291147f, 3.291646f, 3.295029f, 3.296111f, 3.297824f, 3.299148f, 3.300301f,
        3.298320f, 3.300788f, 3.303555f, 3.301762f, 3.298743f, 3.296060f, 3.297781f, 3.305078f,
        3.303180f, 3.303140f, 3.303489f, 3.304173f, 3.304428f, 3.307437f, 3.304637f, 3.303873f,
        3.305207f, 3.308118f, 3.311656f, 3.311736f, 3.308752f, 3.306375f, 3.311665f, 3.305179f,
        3.315337f, 3.327291f, 3.326320f, 3.326952f, 3.328359f, 3.332945f, 3.329615f, 3.326368f,
        3.327381f, 3.330312f, 3.327743f, 3.327218f, 3.327516f, 3.333865f, 3.331078f, 3.335598f,
        3.351215f, 3.365816f, 3.415912f, 3.536410f
    },
    // Temperature: 13.02°C
    {
        3.098287f, 3.118131f, 3.126830f, 3.139764f, 3.143028f, 3.156508f, 3.159801f, 3.164646f,
        3.178089f, 3.175395f, 3.183678f, 3.193254f, 3.198841f, 3.200643f, 3.208278f, 3.213328f,
        3.216153f, 3.219542f, 3.228335f, 3.235108f, 3.238657f, 3.238103f, 3.239212f, 3.243186f,
        3.243905f, 3.246148f, 3.251003f, 3.253736f, 3.254792f, 3.256978f, 3.256223f, 3.258848f,
        3.265872f, 3.267405f, 3.275975f, 3.275198f, 3.276256f, 3.277838f, 3.278438f, 3.278649f,
        3.282675f, 3.281847f, 3.278988f, 3.284798f, 3.284491f, 3.286927f, 3.292385f, 3.290609f,
        3.291838f, 3.292856f, 3.295236f, 3.296641f, 3.299044f, 3.306343f, 3.308771f, 3.311594f,
        3.310075f, 3.313586f, 3.313968f, 3.315924f, 3.316330f, 3.318043f, 3.318825f, 3.320931f,
        3.314392f, 3.317934f, 3.318758f, 3.318731f, 3.322765f, 3.320673f, 3.321566f, 3.320977f,
        3.324259f, 3.326916f, 3.324734f, 3.324787f, 3.327584f, 3.327892f, 3.327772f, 3.329799f,
        3.327982f, 3.327398f, 3.330061f, 3.328982f, 3.327448f, 3.328579f, 3.331256f, 3.329218f,
        3.330005f, 3.329805f, 3.329709f, 3.331501f, 3.334604f, 3.337148f, 3.336821f, 3.352697f,
        3.355486f, 3.366176f, 3.399610f, 3.492515f
    },
    // Temperature: 27.24°C
    {
        3.069642f, 3.103035f, 3.118970f, 3.133688f, 3.146578f, 3.158229f, 3.179125f, 3.182253f,
        3.189087f, 3.195477f, 3.214459f, 3.211953f, 3.220492f, 3.226136f, 3.233271f, 3.236364f,
        3.245178f, 3.255872f, 3.254736f, 3.256442f, 3.254460f, 3.260179f, 3.264256f, 3.267384f,
        3.268892f, 3.271651f, 3.270422f, 3.270855f, 3.272829f, 3.277880f, 3.277542f, 3.284038f,
        3.282812f, 3.286430f, 3.286825f, 3.290545f, 3.291285f, 3.291152f, 3.291507f, 3.293154f,
        3.295571f, 3.292127f, 3.292445f, 3.293031f, 3.295990f, 3.293538f, 3.293874f, 3.294739f,
        3.296521f, 3.296235f, 3.296139f, 3.298737f, 3.297603f, 3.300147f, 3.303376f, 3.303877f,
        3.305770f, 3.309319f, 3.310430f, 3.310297f, 3.313498f, 3.316676f, 3.325925f, 3.329739f,
        3.331764f, 3.333221f, 3.332947f, 3.330488f, 3.329748f, 3.332285f, 3.333160f, 3.334500f,
        3.334786f, 3.328979f, 3.331396f, 3.328641f, 3.329749f, 3.331654f, 3.334552f, 3.334886f,
        3.330571f, 3.331605f, 3.332474f, 3.331966f, 3.332839f, 3.331973f, 3.334700f, 3.334794f,
        3.332914f, 3.333407f, 3.334523f, 3.330442f, 3.332919f, 3.335184f, 3.334255f, 3.340670f,
        3.345690f, 3.372667f, 3.391779f, 3.499171f
    },
    // Temperature: 38.15°C
    {
        3.087556f, 3.126632f, 3.148566f, 3.168815f, 3.172105f, 3.178373f, 3.178764f, 3.182555f,
        3.186842f, 3.197390f, 3.207123f, 3.214296f, 3.215855f, 3.224203f, 3.231342f, 3.229358f,
        3.245378f, 3.245246f, 3.246536f, 3.250132f, 3.254873f, 3.256908f, 3.265109f, 3.266418f,
        3.267498f, 3.273707f, 3.274927f, 3.273139f, 3.277718f, 3.284035f, 3.281972f, 3.282310f,
        3.283787f, 3.286228f, 3.287596f, 3.289027f, 3.288843f, 3.291216f, 3.295023f, 3.293810f,
        3.293395f, 3.293855f, 3.293698f, 3.288968f, 3.291762f, 3.293569f, 3.293601f, 3.293836f,
        3.296357f, 3.295530f, 3.298651f, 3.300974f, 3.303485f, 3.305334f, 3.303963f, 3.308351f,
        3.307935f, 3.311733f, 3.309202f, 3.312710f, 3.312796f, 3.317275f, 3.322755f, 3.327882f,
        3.331391f, 3.332052f, 3.328511f, 3.323916f, 3.325830f, 3.330451f, 3.332108f, 3.331182f,
        3.330901f, 3.332280f, 3.330971f, 3.331472f, 3.330202f, 3.333274f, 3.331861f, 3.331974f,
        3.330172f, 3.325949f, 3.325060f, 3.327593f, 3.333727f, 3.334520f, 3.334119f, 3.334330f,
        3.335265f, 3.335022f, 3.334783f, 3.338244f, 3.338093f, 3.332496f, 3.333580f, 3.337004f,
        3.352774f, 3.377433f, 3.401094f, 3.539791f
    }
};

// Function declarations
/**
 * Get internal resistance at specified temperature
 * @param temperature Battery temperature in Celsius
 * @return Interpolated internal resistance (ohms)
 */
float battery_get_internal_resistance(float temperature);

/**
 * Get battery capacity at specified temperature
 * @param temperature Battery temperature in Celsius
 * @return Interpolated capacity (mAh)
 */
float battery_get_capacity(float temperature);

/**
 * Get open circuit voltage for given SoC and temperature
 * @param soc State of Charge (0.0 to 1.0)
 * @param temperature Battery temperature in Celsius
 * @return Open circuit voltage (V)
 */
float battery_get_voc(float soc, float temperature);

/**
 * Get State of Charge for given open circuit voltage and temperature
 * @param voc Open circuit voltage (V)
 * @param temperature Battery temperature in Celsius
 * @return State of Charge (0.0 to 1.0)
 */
float battery_get_soc(float voc, float temperature);

#endif // BATTERY_LOOKUP_TABLES_H