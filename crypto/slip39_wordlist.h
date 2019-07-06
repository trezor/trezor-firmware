/**
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include <stdint.h>

#define WORDS_COUNT 1024

static const char* const wordlist[WORDS_COUNT] = {
    "academic", "acid",     "acne",     "acquire",  "acrobat",  "activity",
    "actress",  "adapt",    "adequate", "adjust",   "admit",    "adorn",
    "adult",    "advance",  "advocate", "afraid",   "again",    "agency",
    "agree",    "aide",     "aircraft", "airline",  "airport",  "ajar",
    "alarm",    "album",    "alcohol",  "alien",    "alive",    "alpha",
    "already",  "alto",     "aluminum", "always",   "amazing",  "ambition",
    "amount",   "amuse",    "analysis", "anatomy",  "ancestor", "ancient",
    "angel",    "angry",    "animal",   "answer",   "antenna",  "anxiety",
    "apart",    "aquatic",  "arcade",   "arena",    "argue",    "armed",
    "artist",   "artwork",  "aspect",   "auction",  "august",   "aunt",
    "average",  "aviation", "avoid",    "award",    "away",     "axis",
    "axle",     "beam",     "beard",    "beaver",   "become",   "bedroom",
    "behavior", "being",    "believe",  "belong",   "benefit",  "best",
    "beyond",   "bike",     "biology",  "birthday", "bishop",   "black",
    "blanket",  "blessing", "blimp",    "blind",    "blue",     "body",
    "bolt",     "boring",   "born",     "both",     "boundary", "bracelet",
    "branch",   "brave",    "breathe",  "briefing", "broken",   "brother",
    "browser",  "bucket",   "budget",   "building", "bulb",     "bulge",
    "bumpy",    "bundle",   "burden",   "burning",  "busy",     "buyer",
    "cage",     "calcium",  "camera",   "campus",   "canyon",   "capacity",
    "capital",  "capture",  "carbon",   "cards",    "careful",  "cargo",
    "carpet",   "carve",    "category", "cause",    "ceiling",  "center",
    "ceramic",  "champion", "change",   "charity",  "check",    "chemical",
    "chest",    "chew",     "chubby",   "cinema",   "civil",    "class",
    "clay",     "cleanup",  "client",   "climate",  "clinic",   "clock",
    "clogs",    "closet",   "clothes",  "club",     "cluster",  "coal",
    "coastal",  "coding",   "column",   "company",  "corner",   "costume",
    "counter",  "course",   "cover",    "cowboy",   "cradle",   "craft",
    "crazy",    "credit",   "cricket",  "criminal", "crisis",   "critical",
    "crowd",    "crucial",  "crunch",   "crush",    "crystal",  "cubic",
    "cultural", "curious",  "curly",    "custody",  "cylinder", "daisy",
    "damage",   "dance",    "darkness", "database", "daughter", "deadline",
    "deal",     "debris",   "debut",    "decent",   "decision", "declare",
    "decorate", "decrease", "deliver",  "demand",   "density",  "deny",
    "depart",   "depend",   "depict",   "deploy",   "describe", "desert",
    "desire",   "desktop",  "destroy",  "detailed", "detect",   "device",
    "devote",   "diagnose", "dictate",  "diet",     "dilemma",  "diminish",
    "dining",   "diploma",  "disaster", "discuss",  "disease",  "dish",
    "dismiss",  "display",  "distance", "dive",     "divorce",  "document",
    "domain",   "domestic", "dominant", "dough",    "downtown", "dragon",
    "dramatic", "dream",    "dress",    "drift",    "drink",    "drove",
    "drug",     "dryer",    "duckling", "duke",     "duration", "dwarf",
    "dynamic",  "early",    "earth",    "easel",    "easy",     "echo",
    "eclipse",  "ecology",  "edge",     "editor",   "educate",  "either",
    "elbow",    "elder",    "election", "elegant",  "element",  "elephant",
    "elevator", "elite",    "else",     "email",    "emerald",  "emission",
    "emperor",  "emphasis", "employer", "empty",    "ending",   "endless",
    "endorse",  "enemy",    "energy",   "enforce",  "engage",   "enjoy",
    "enlarge",  "entrance", "envelope", "envy",     "epidemic", "episode",
    "equation", "equip",    "eraser",   "erode",    "escape",   "estate",
    "estimate", "evaluate", "evening",  "evidence", "evil",     "evoke",
    "exact",    "example",  "exceed",   "exchange", "exclude",  "excuse",
    "execute",  "exercise", "exhaust",  "exotic",   "expand",   "expect",
    "explain",  "express",  "extend",   "extra",    "eyebrow",  "facility",
    "fact",     "failure",  "faint",    "fake",     "false",    "family",
    "famous",   "fancy",    "fangs",    "fantasy",  "fatal",    "fatigue",
    "favorite", "fawn",     "fiber",    "fiction",  "filter",   "finance",
    "findings", "finger",   "firefly",  "firm",     "fiscal",   "fishing",
    "fitness",  "flame",    "flash",    "flavor",   "flea",     "flexible",
    "flip",     "float",    "floral",   "fluff",    "focus",    "forbid",
    "force",    "forecast", "forget",   "formal",   "fortune",  "forward",
    "founder",  "fraction", "fragment", "frequent", "freshman", "friar",
    "fridge",   "friendly", "frost",    "froth",    "frozen",   "fumes",
    "funding",  "furl",     "fused",    "galaxy",   "game",     "garbage",
    "garden",   "garlic",   "gasoline", "gather",   "general",  "genius",
    "genre",    "genuine",  "geology",  "gesture",  "glad",     "glance",
    "glasses",  "glen",     "glimpse",  "goat",     "golden",   "graduate",
    "grant",    "grasp",    "gravity",  "gray",     "greatest", "grief",
    "grill",    "grin",     "grocery",  "gross",    "group",    "grownup",
    "grumpy",   "guard",    "guest",    "guilt",    "guitar",   "gums",
    "hairy",    "hamster",  "hand",     "hanger",   "harvest",  "have",
    "havoc",    "hawk",     "hazard",   "headset",  "health",   "hearing",
    "heat",     "helpful",  "herald",   "herd",     "hesitate", "hobo",
    "holiday",  "holy",     "home",     "hormone",  "hospital", "hour",
    "huge",     "human",    "humidity", "hunting",  "husband",  "hush",
    "husky",    "hybrid",   "idea",     "identify", "idle",     "image",
    "impact",   "imply",    "improve",  "impulse",  "include",  "income",
    "increase", "index",    "indicate", "industry", "infant",   "inform",
    "inherit",  "injury",   "inmate",   "insect",   "inside",   "install",
    "intend",   "intimate", "invasion", "involve",  "iris",     "island",
    "isolate",  "item",     "ivory",    "jacket",   "jerky",    "jewelry",
    "join",     "judicial", "juice",    "jump",     "junction", "junior",
    "junk",     "jury",     "justice",  "kernel",   "keyboard", "kidney",
    "kind",     "kitchen",  "knife",    "knit",     "laden",    "ladle",
    "ladybug",  "lair",     "lamp",     "language", "large",    "laser",
    "laundry",  "lawsuit",  "leader",   "leaf",     "learn",    "leaves",
    "lecture",  "legal",    "legend",   "legs",     "lend",     "length",
    "level",    "liberty",  "library",  "license",  "lift",     "likely",
    "lilac",    "lily",     "lips",     "liquid",   "listen",   "literary",
    "living",   "lizard",   "loan",     "lobe",     "location", "losing",
    "loud",     "loyalty",  "luck",     "lunar",    "lunch",    "lungs",
    "luxury",   "lying",    "lyrics",   "machine",  "magazine", "maiden",
    "mailman",  "main",     "makeup",   "making",   "mama",     "manager",
    "mandate",  "mansion",  "manual",   "marathon", "march",    "market",
    "marvel",   "mason",    "material", "math",     "maximum",  "mayor",
    "meaning",  "medal",    "medical",  "member",   "memory",   "mental",
    "merchant", "merit",    "method",   "metric",   "midst",    "mild",
    "military", "mineral",  "minister", "miracle",  "mixed",    "mixture",
    "mobile",   "modern",   "modify",   "moisture", "moment",   "morning",
    "mortgage", "mother",   "mountain", "mouse",    "move",     "much",
    "mule",     "multiple", "muscle",   "museum",   "music",    "mustang",
    "nail",     "national", "necklace", "negative", "nervous",  "network",
    "news",     "nuclear",  "numb",     "numerous", "nylon",    "oasis",
    "obesity",  "object",   "observe",  "obtain",   "ocean",    "often",
    "olympic",  "omit",     "oral",     "orange",   "orbit",    "order",
    "ordinary", "organize", "ounce",    "oven",     "overall",  "owner",
    "paces",    "pacific",  "package",  "paid",     "painting", "pajamas",
    "pancake",  "pants",    "papa",     "paper",    "parcel",   "parking",
    "party",    "patent",   "patrol",   "payment",  "payroll",  "peaceful",
    "peanut",   "peasant",  "pecan",    "penalty",  "pencil",   "percent",
    "perfect",  "permit",   "petition", "phantom",  "pharmacy", "photo",
    "phrase",   "physics",  "pickup",   "picture",  "piece",    "pile",
    "pink",     "pipeline", "pistol",   "pitch",    "plains",   "plan",
    "plastic",  "platform", "playoff",  "pleasure", "plot",     "plunge",
    "practice", "prayer",   "preach",   "predator", "pregnant", "premium",
    "prepare",  "presence", "prevent",  "priest",   "primary",  "priority",
    "prisoner", "privacy",  "prize",    "problem",  "process",  "profile",
    "program",  "promise",  "prospect", "provide",  "prune",    "public",
    "pulse",    "pumps",    "punish",   "puny",     "pupal",    "purchase",
    "purple",   "python",   "quantity", "quarter",  "quick",    "quiet",
    "race",     "racism",   "radar",    "railroad", "rainbow",  "raisin",
    "random",   "ranked",   "rapids",   "raspy",    "reaction", "realize",
    "rebound",  "rebuild",  "recall",   "receiver", "recover",  "regret",
    "regular",  "reject",   "relate",   "remember", "remind",   "remove",
    "render",   "repair",   "repeat",   "replace",  "require",  "rescue",
    "research", "resident", "response", "result",   "retailer", "retreat",
    "reunion",  "revenue",  "review",   "reward",   "rhyme",    "rhythm",
    "rich",     "rival",    "river",    "robin",    "rocky",    "romantic",
    "romp",     "roster",   "round",    "royal",    "ruin",     "ruler",
    "rumor",    "sack",     "safari",   "salary",   "salon",    "salt",
    "satisfy",  "satoshi",  "saver",    "says",     "scandal",  "scared",
    "scatter",  "scene",    "scholar",  "science",  "scout",    "scramble",
    "screw",    "script",   "scroll",   "seafood",  "season",   "secret",
    "security", "segment",  "senior",   "shadow",   "shaft",    "shame",
    "shaped",   "sharp",    "shelter",  "sheriff",  "short",    "should",
    "shrimp",   "sidewalk", "silent",   "silver",   "similar",  "simple",
    "single",   "sister",   "skin",     "skunk",    "slap",     "slavery",
    "sled",     "slice",    "slim",     "slow",     "slush",    "smart",
    "smear",    "smell",    "smirk",    "smith",    "smoking",  "smug",
    "snake",    "snapshot", "sniff",    "society",  "software", "soldier",
    "solution", "soul",     "source",   "space",    "spark",    "speak",
    "species",  "spelling", "spend",    "spew",     "spider",   "spill",
    "spine",    "spirit",   "spit",     "spray",    "sprinkle", "square",
    "squeeze",  "stadium",  "staff",    "standard", "starting", "station",
    "stay",     "steady",   "step",     "stick",    "stilt",    "story",
    "strategy", "strike",   "style",    "subject",  "submit",   "sugar",
    "suitable", "sunlight", "superior", "surface",  "surprise", "survive",
    "sweater",  "swimming", "swing",    "switch",   "symbolic", "sympathy",
    "syndrome", "system",   "tackle",   "tactics",  "tadpole",  "talent",
    "task",     "taste",    "taught",   "taxi",     "teacher",  "teammate",
    "teaspoon", "temple",   "tenant",   "tendency", "tension",  "terminal",
    "testify",  "texture",  "thank",    "that",     "theater",  "theory",
    "therapy",  "thorn",    "threaten", "thumb",    "thunder",  "ticket",
    "tidy",     "timber",   "timely",   "ting",     "tofu",     "together",
    "tolerate", "total",    "toxic",    "tracks",   "traffic",  "training",
    "transfer", "trash",    "traveler", "treat",    "trend",    "trial",
    "tricycle", "trip",     "triumph",  "trouble",  "true",     "trust",
    "twice",    "twin",     "type",     "typical",  "ugly",     "ultimate",
    "umbrella", "uncover",  "undergo",  "unfair",   "unfold",   "unhappy",
    "union",    "universe", "unkind",   "unknown",  "unusual",  "unwrap",
    "upgrade",  "upstairs", "username", "usher",    "usual",    "valid",
    "valuable", "vampire",  "vanish",   "various",  "vegan",    "velvet",
    "venture",  "verdict",  "verify",   "very",     "veteran",  "vexed",
    "victim",   "video",    "view",     "vintage",  "violence", "viral",
    "visitor",  "visual",   "vitamins", "vocal",    "voice",    "volume",
    "voter",    "voting",   "walnut",   "warmth",   "warn",     "watch",
    "wavy",     "wealthy",  "weapon",   "webcam",   "welcome",  "welfare",
    "western",  "width",    "wildlife", "window",   "wine",     "wireless",
    "wisdom",   "withdraw", "wits",     "wolf",     "woman",    "work",
    "worthy",   "wrap",     "wrist",    "writing",  "wrote",    "year",
    "yelp",     "yield",    "yoga",     "zero",
};

/**
 * This array contains number representations of SLIP-39 words.
 * These numbers are determined how the words were entered on a
 * T9 keyboard with the following layout:
 *     ab (1)   cd (2)  ef (3)
 *     ghij (4) klm (5) nopq (6)
 *     rs (7)   tuv (8) wxyz (9)
 *
 * Each word is uniquely defined by four buttons.
 */
static const uint16_t words_button_seq[WORDS_COUNT] = {
    1212,  // academic
    1242,  // acid
    1263,  // acne
    1268,  // acquire
    1276,  // acrobat
    1284,  // activity
    1287,  // actress
    1216,  // adapt
    1236,  // adequate
    1248,  // adjust
    1254,  // admit
    1267,  // adorn
    1285,  // adult
    1281,  // advance
    1286,  // advocate
    1371,  // afraid
    1414,  // again
    1436,  // agency
    1473,  // agree
    1423,  // aide
    1472,  // aircraft
    1475,  // airline
    1476,  // airport
    1417,  // ajar
    1517,  // alarm
    1518,  // album
    1526,  // alcohol
    1543,  // alien
    1548,  // alive
    1564,  // alpha
    1573,  // already
    1586,  // alto
    1585,  // aluminum
    1591,  // always
    1519,  // amazing
    1514,  // ambition
    1568,  // amount
    1587,  // amuse
    1615,  // analysis
    1618,  // anatomy
    1623,  // ancestor
    1624,  // ancient
    1643,  // angel
    1647,  // angry
    1645,  // animal
    1679,  // answer
    1683,  // antenna
    1694,  // anxiety
    1617,  // apart
    1681,  // aquatic
    1721,  // arcade
    1736,  // arena
    1748,  // argue
    1753,  // armed
    1784,  // artist
    1789,  // artwork
    1763,  // aspect
    1828,  // auction
    1848,  // august
    1868,  // aunt
    1837,  // average
    1841,  // aviation
    1864,  // avoid
    1917,  // award
    1919,  // away
    1947,  // axis
    1953,  // axle
    1315,  // beam
    1317,  // beard
    1318,  // beaver
    1326,  // become
    1327,  // bedroom
    1341,  // behavior
    1346,  // being
    1354,  // believe
    1356,  // belong
    1363,  // benefit
    1378,  // best
    1396,  // beyond
    1453,  // bike
    1465,  // biology
    1478,  // birthday
    1474,  // bishop
    1512,  // black
    1516,  // blanket
    1537,  // blessing
    1545,  // blimp
    1546,  // blind
    1583,  // blue
    1629,  // body
    1658,  // bolt
    1674,  // boring
    1676,  // born
    1684,  // both
    1686,  // boundary
    1712,  // bracelet
    1716,  // branch
    1718,  // brave
    1731,  // breathe
    1743,  // briefing
    1765,  // broken
    1768,  // brother
    1769,  // browser
    1825,  // bucket
    1824,  // budget
    1845,  // building
    1851,  // bulb
    1854,  // bulge
    1856,  // bumpy
    1862,  // bundle
    1872,  // burden
    1876,  // burning
    1879,  // busy
    1893,  // buyer
    2143,  // cage
    2152,  // calcium
    2153,  // camera
    2156,  // campus
    2169,  // canyon
    2161,  // capacity
    2164,  // capital
    2168,  // capture
    2171,  // carbon
    2172,  // cards
    2173,  // careful
    2174,  // cargo
    2176,  // carpet
    2178,  // carve
    2183,  // category
    2187,  // cause
    2345,  // ceiling
    2368,  // center
    2371,  // ceramic
    2415,  // champion
    2416,  // change
    2417,  // charity
    2432,  // check
    2435,  // chemical
    2437,  // chest
    2439,  // chew
    2481,  // chubby
    2463,  // cinema
    2484,  // civil
    2517,  // class
    2519,  // clay
    2531,  // cleanup
    2543,  // client
    2545,  // climate
    2546,  // clinic
    2562,  // clock
    2564,  // clogs
    2567,  // closet
    2568,  // clothes
    2581,  // club
    2587,  // cluster
    2615,  // coal
    2617,  // coastal
    2624,  // coding
    2658,  // column
    2656,  // company
    2676,  // corner
    2678,  // costume
    2686,  // counter
    2687,  // course
    2683,  // cover
    2691,  // cowboy
    2712,  // cradle
    2713,  // craft
    2719,  // crazy
    2732,  // credit
    2742,  // cricket
    2745,  // criminal
    2747,  // crisis
    2748,  // critical
    2769,  // crowd
    2782,  // crucial
    2786,  // crunch
    2787,  // crush
    2797,  // crystal
    2814,  // cubic
    2858,  // cultural
    2874,  // curious
    2875,  // curly
    2878,  // custody
    2954,  // cylinder
    2147,  // daisy
    2151,  // damage
    2162,  // dance
    2175,  // darkness
    2181,  // database
    2184,  // daughter
    2312,  // deadline
    2315,  // deal
    2317,  // debris
    2318,  // debut
    2323,  // decent
    2324,  // decision
    2325,  // declare
    2326,  // decorate
    2327,  // decrease
    2354,  // deliver
    2351,  // demand
    2367,  // density
    2369,  // deny
    2361,  // depart
    2363,  // depend
    2364,  // depict
    2365,  // deploy
    2372,  // describe
    2373,  // desert
    2374,  // desire
    2375,  // desktop
    2378,  // destroy
    2381,  // detailed
    2383,  // detect
    2384,  // device
    2386,  // devote
    2414,  // diagnose
    2428,  // dictate
    2438,  // diet
    2453,  // dilemma
    2454,  // diminish
    2464,  // dining
    2465,  // diploma
    2471,  // disaster
    2472,  // discuss
    2473,  // disease
    2474,  // dish
    2475,  // dismiss
    2476,  // display
    2478,  // distance
    2483,  // dive
    2486,  // divorce
    2628,  // document
    2651,  // domain
    2653,  // domestic
    2654,  // dominant
    2684,  // dough
    2696,  // downtown
    2714,  // dragon
    2715,  // dramatic
    2731,  // dream
    2737,  // dress
    2743,  // drift
    2746,  // drink
    2768,  // drove
    2784,  // drug
    2793,  // dryer
    2825,  // duckling
    2853,  // duke
    2871,  // duration
    2917,  // dwarf
    2961,  // dynamic
    3175,  // early
    3178,  // earth
    3173,  // easel
    3179,  // easy
    3246,  // echo
    3254,  // eclipse
    3265,  // ecology
    3243,  // edge
    3248,  // editor
    3282,  // educate
    3484,  // either
    3516,  // elbow
    3523,  // elder
    3532,  // election
    3534,  // elegant
    3535,  // element
    3536,  // elephant
    3538,  // elevator
    3548,  // elite
    3573,  // else
    3514,  // email
    3537,  // emerald
    3547,  // emission
    3563,  // emperor
    3564,  // emphasis
    3565,  // employer
    3568,  // empty
    3624,  // ending
    3625,  // endless
    3626,  // endorse
    3635,  // enemy
    3637,  // energy
    3636,  // enforce
    3641,  // engage
    3646,  // enjoy
    3651,  // enlarge
    3687,  // entrance
    3683,  // envelope
    3689,  // envy
    3642,  // epidemic
    3647,  // episode
    3681,  // equation
    3684,  // equip
    3717,  // eraser
    3762,  // erode
    3721,  // escape
    3781,  // estate
    3784,  // estimate
    3815,  // evaluate
    3836,  // evening
    3842,  // evidence
    3845,  // evil
    3865,  // evoke
    3912,  // exact
    3915,  // example
    3923,  // exceed
    3924,  // exchange
    3925,  // exclude
    3928,  // excuse
    3932,  // execute
    3937,  // exercise
    3941,  // exhaust
    3968,  // exotic
    3961,  // expand
    3963,  // expect
    3965,  // explain
    3967,  // express
    3983,  // extend
    3987,  // extra
    3931,  // eyebrow
    3124,  // facility
    3128,  // fact
    3145,  // failure
    3146,  // faint
    3153,  // fake
    3157,  // false
    3154,  // family
    3156,  // famous
    3162,  // fancy
    3164,  // fangs
    3168,  // fantasy
    3181,  // fatal
    3184,  // fatigue
    3186,  // favorite
    3196,  // fawn
    3413,  // fiber
    3428,  // fiction
    3458,  // filter
    3461,  // finance
    3462,  // findings
    3464,  // finger
    3473,  // firefly
    3475,  // firm
    3472,  // fiscal
    3474,  // fishing
    3486,  // fitness
    3515,  // flame
    3517,  // flash
    3518,  // flavor
    3531,  // flea
    3539,  // flexible
    3546,  // flip
    3561,  // float
    3567,  // floral
    3583,  // fluff
    3628,  // focus
    3671,  // forbid
    3672,  // force
    3673,  // forecast
    3674,  // forget
    3675,  // formal
    3678,  // fortune
    3679,  // forward
    3686,  // founder
    3712,  // fraction
    3714,  // fragment
    3736,  // frequent
    3737,  // freshman
    3741,  // friar
    3742,  // fridge
    3743,  // friendly
    3767,  // frost
    3768,  // froth
    3769,  // frozen
    3853,  // fumes
    3862,  // funding
    3875,  // furl
    3873,  // fused
    4151,  // galaxy
    4153,  // game
    4171,  // garbage
    4172,  // garden
    4175,  // garlic
    4176,  // gasoline
    4184,  // gather
    4363,  // general
    4364,  // genius
    4367,  // genre
    4368,  // genuine
    4365,  // geology
    4378,  // gesture
    4512,  // glad
    4516,  // glance
    4517,  // glasses
    4536,  // glen
    4545,  // glimpse
    4618,  // goat
    4652,  // golden
    4712,  // graduate
    4716,  // grant
    4717,  // grasp
    4718,  // gravity
    4719,  // gray
    4731,  // greatest
    4743,  // grief
    4745,  // grill
    4746,  // grin
    4762,  // grocery
    4767,  // gross
    4768,  // group
    4769,  // grownup
    4785,  // grumpy
    4817,  // guard
    4837,  // guest
    4845,  // guilt
    4848,  // guitar
    4857,  // gums
    4147,  // hairy
    4157,  // hamster
    4162,  // hand
    4164,  // hanger
    4178,  // harvest
    4183,  // have
    4186,  // havoc
    4195,  // hawk
    4191,  // hazard
    4312,  // headset
    4315,  // health
    4317,  // hearing
    4318,  // heat
    4356,  // helpful
    4371,  // herald
    4372,  // herd
    4374,  // hesitate
    4616,  // hobo
    4654,  // holiday
    4659,  // holy
    4653,  // home
    4675,  // hormone
    4676,  // hospital
    4687,  // hour
    4843,  // huge
    4851,  // human
    4854,  // humidity
    4868,  // hunting
    4871,  // husband
    4874,  // hush
    4875,  // husky
    4917,  // hybrid
    4231,  // idea
    4236,  // identify
    4253,  // idle
    4514,  // image
    4561,  // impact
    4565,  // imply
    4567,  // improve
    4568,  // impulse
    4625,  // include
    4626,  // income
    4627,  // increase
    4623,  // index
    4624,  // indicate
    4628,  // industry
    4631,  // infant
    4636,  // inform
    4643,  // inherit
    4648,  // injury
    4651,  // inmate
    4673,  // insect
    4674,  // inside
    4678,  // install
    4683,  // intend
    4684,  // intimate
    4681,  // invasion
    4686,  // involve
    4747,  // iris
    4751,  // island
    4765,  // isolate
    4835,  // item
    4867,  // ivory
    4125,  // jacket
    4375,  // jerky
    4393,  // jewelry
    4646,  // join
    4824,  // judicial
    4842,  // juice
    4856,  // jump
    4862,  // junction
    4864,  // junior
    4865,  // junk
    4879,  // jury
    4878,  // justice
    5376,  // kernel
    5391,  // keyboard
    5426,  // kidney
    5462,  // kind
    5482,  // kitchen
    5643,  // knife
    5648,  // knit
    5123,  // laden
    5125,  // ladle
    5129,  // ladybug
    5147,  // lair
    5156,  // lamp
    5164,  // language
    5174,  // large
    5173,  // laser
    5186,  // laundry
    5197,  // lawsuit
    5312,  // leader
    5313,  // leaf
    5317,  // learn
    5318,  // leaves
    5328,  // lecture
    5341,  // legal
    5343,  // legend
    5347,  // legs
    5362,  // lend
    5364,  // length
    5383,  // level
    5413,  // liberty
    5417,  // library
    5423,  // license
    5438,  // lift
    5453,  // likely
    5451,  // lilac
    5459,  // lily
    5467,  // lips
    5468,  // liquid
    5478,  // listen
    5483,  // literary
    5484,  // living
    5491,  // lizard
    5616,  // loan
    5613,  // lobe
    5621,  // location
    5674,  // losing
    5682,  // loud
    5691,  // loyalty
    5825,  // luck
    5861,  // lunar
    5862,  // lunch
    5864,  // lungs
    5898,  // luxury
    5946,  // lying
    5974,  // lyrics
    5124,  // machine
    5141,  // magazine
    5142,  // maiden
    5145,  // mailman
    5146,  // main
    5153,  // makeup
    5154,  // making
    5151,  // mama
    5161,  // manager
    5162,  // mandate
    5167,  // mansion
    5168,  // manual
    5171,  // marathon
    5172,  // march
    5175,  // market
    5178,  // marvel
    5176,  // mason
    5183,  // material
    5184,  // math
    5194,  // maximum
    5196,  // mayor
    5316,  // meaning
    5321,  // medal
    5324,  // medical
    5351,  // member
    5356,  // memory
    5368,  // mental
    5372,  // merchant
    5374,  // merit
    5384,  // method
    5387,  // metric
    5427,  // midst
    5452,  // mild
    5454,  // military
    5463,  // mineral
    5464,  // minister
    5471,  // miracle
    5493,  // mixed
    5498,  // mixture
    5614,  // mobile
    5623,  // modern
    5624,  // modify
    5647,  // moisture
    5653,  // moment
    5676,  // morning
    5678,  // mortgage
    5684,  // mother
    5686,  // mountain
    5687,  // mouse
    5683,  // move
    5824,  // much
    5853,  // mule
    5858,  // multiple
    5872,  // muscle
    5873,  // museum
    5874,  // music
    5878,  // mustang
    6145,  // nail
    6184,  // national
    6325,  // necklace
    6341,  // negative
    6378,  // nervous
    6389,  // network
    6397,  // news
    6825,  // nuclear
    6851,  // numb
    6853,  // numerous
    6956,  // nylon
    6174,  // oasis
    6137,  // obesity
    6143,  // object
    6173,  // observe
    6181,  // obtain
    6231,  // ocean
    6383,  // often
    6595,  // olympic
    6548,  // omit
    6715,  // oral
    6716,  // orange
    6714,  // orbit
    6723,  // order
    6724,  // ordinary
    6741,  // organize
    6862,  // ounce
    6836,  // oven
    6837,  // overall
    6963,  // owner
    6123,  // paces
    6124,  // pacific
    6125,  // package
    6142,  // paid
    6146,  // painting
    6141,  // pajamas
    6162,  // pancake
    6168,  // pants
    6161,  // papa
    6163,  // paper
    6172,  // parcel
    6175,  // parking
    6178,  // party
    6183,  // patent
    6187,  // patrol
    6195,  // payment
    6197,  // payroll
    6312,  // peaceful
    6316,  // peanut
    6317,  // peasant
    6321,  // pecan
    6361,  // penalty
    6362,  // pencil
    6372,  // percent
    6373,  // perfect
    6375,  // permit
    6384,  // petition
    6416,  // phantom
    6417,  // pharmacy
    6468,  // photo
    6471,  // phrase
    6497,  // physics
    6425,  // pickup
    6428,  // picture
    6432,  // piece
    6453,  // pile
    6465,  // pink
    6463,  // pipeline
    6478,  // pistol
    6482,  // pitch
    6514,  // plains
    6516,  // plan
    6517,  // plastic
    6518,  // platform
    6519,  // playoff
    6531,  // pleasure
    6568,  // plot
    6586,  // plunge
    6712,  // practice
    6719,  // prayer
    6731,  // preach
    6732,  // predator
    6734,  // pregnant
    6735,  // premium
    6736,  // prepare
    6737,  // presence
    6738,  // prevent
    6743,  // priest
    6745,  // primary
    6746,  // priority
    6747,  // prisoner
    6748,  // privacy
    6749,  // prize
    6761,  // problem
    6762,  // process
    6763,  // profile
    6764,  // program
    6765,  // promise
    6767,  // prospect
    6768,  // provide
    6786,  // prune
    6815,  // public
    6857,  // pulse
    6856,  // pumps
    6864,  // punish
    6869,  // puny
    6861,  // pupal
    6872,  // purchase
    6876,  // purple
    6984,  // python
    6816,  // quantity
    6817,  // quarter
    6842,  // quick
    6843,  // quiet
    7123,  // race
    7124,  // racism
    7121,  // radar
    7145,  // railroad
    7146,  // rainbow
    7147,  // raisin
    7162,  // random
    7165,  // ranked
    7164,  // rapids
    7176,  // raspy
    7312,  // reaction
    7315,  // realize
    7316,  // rebound
    7318,  // rebuild
    7321,  // recall
    7323,  // receiver
    7326,  // recover
    7347,  // regret
    7348,  // regular
    7343,  // reject
    7351,  // relate
    7353,  // remember
    7354,  // remind
    7356,  // remove
    7362,  // render
    7361,  // repair
    7363,  // repeat
    7365,  // replace
    7368,  // require
    7372,  // rescue
    7373,  // research
    7374,  // resident
    7376,  // response
    7378,  // result
    7381,  // retailer
    7387,  // retreat
    7386,  // reunion
    7383,  // revenue
    7384,  // review
    7391,  // reward
    7495,  // rhyme
    7498,  // rhythm
    7424,  // rich
    7481,  // rival
    7483,  // river
    7614,  // robin
    7625,  // rocky
    7651,  // romantic
    7656,  // romp
    7678,  // roster
    7686,  // round
    7691,  // royal
    7846,  // ruin
    7853,  // ruler
    7856,  // rumor
    7125,  // sack
    7131,  // safari
    7151,  // salary
    7156,  // salon
    7158,  // salt
    7184,  // satisfy
    7186,  // satoshi
    7183,  // saver
    7197,  // says
    7216,  // scandal
    7217,  // scared
    7218,  // scatter
    7236,  // scene
    7246,  // scholar
    7243,  // science
    7268,  // scout
    7271,  // scramble
    7273,  // screw
    7274,  // script
    7276,  // scroll
    7313,  // seafood
    7317,  // season
    7327,  // secret
    7328,  // security
    7345,  // segment
    7364,  // senior
    7412,  // shadow
    7413,  // shaft
    7415,  // shame
    7416,  // shaped
    7417,  // sharp
    7435,  // shelter
    7437,  // sheriff
    7467,  // short
    7468,  // should
    7474,  // shrimp
    7423,  // sidewalk
    7453,  // silent
    7458,  // silver
    7454,  // similar
    7456,  // simple
    7464,  // single
    7478,  // sister
    7546,  // skin
    7586,  // skunk
    7516,  // slap
    7518,  // slavery
    7532,  // sled
    7542,  // slice
    7545,  // slim
    7569,  // slow
    7587,  // slush
    7517,  // smart
    7531,  // smear
    7535,  // smell
    7547,  // smirk
    7548,  // smith
    7565,  // smoking
    7584,  // smug
    7615,  // snake
    7616,  // snapshot
    7643,  // sniff
    7624,  // society
    7638,  // software
    7652,  // soldier
    7658,  // solution
    7685,  // soul
    7687,  // source
    7612,  // space
    7617,  // spark
    7631,  // speak
    7632,  // species
    7635,  // spelling
    7636,  // spend
    7639,  // spew
    7642,  // spider
    7645,  // spill
    7646,  // spine
    7647,  // spirit
    7648,  // spit
    7671,  // spray
    7674,  // sprinkle
    7681,  // square
    7683,  // squeeze
    7812,  // stadium
    7813,  // staff
    7816,  // standard
    7817,  // starting
    7818,  // station
    7819,  // stay
    7831,  // steady
    7836,  // step
    7842,  // stick
    7845,  // stilt
    7867,  // story
    7871,  // strategy
    7874,  // strike
    7895,  // style
    7814,  // subject
    7815,  // submit
    7841,  // sugar
    7848,  // suitable
    7865,  // sunlight
    7863,  // superior
    7873,  // surface
    7876,  // surprise
    7878,  // survive
    7931,  // sweater
    7945,  // swimming
    7946,  // swing
    7948,  // switch
    7951,  // symbolic
    7956,  // sympathy
    7962,  // syndrome
    7978,  // system
    8125,  // tackle
    8128,  // tactics
    8126,  // tadpole
    8153,  // talent
    8175,  // task
    8178,  // taste
    8184,  // taught
    8194,  // taxi
    8312,  // teacher
    8315,  // teammate
    8317,  // teaspoon
    8356,  // temple
    8361,  // tenant
    8362,  // tendency
    8367,  // tension
    8375,  // terminal
    8378,  // testify
    8398,  // texture
    8416,  // thank
    8418,  // that
    8431,  // theater
    8436,  // theory
    8437,  // therapy
    8467,  // thorn
    8473,  // threaten
    8485,  // thumb
    8486,  // thunder
    8425,  // ticket
    8429,  // tidy
    8451,  // timber
    8453,  // timely
    8464,  // ting
    8638,  // tofu
    8643,  // together
    8653,  // tolerate
    8681,  // total
    8694,  // toxic
    8712,  // tracks
    8713,  // traffic
    8714,  // training
    8716,  // transfer
    8717,  // trash
    8718,  // traveler
    8731,  // treat
    8736,  // trend
    8741,  // trial
    8742,  // tricycle
    8746,  // trip
    8748,  // triumph
    8768,  // trouble
    8783,  // true
    8787,  // trust
    8942,  // twice
    8946,  // twin
    8963,  // type
    8964,  // typical
    8459,  // ugly
    8584,  // ultimate
    8517,  // umbrella
    8626,  // uncover
    8623,  // undergo
    8631,  // unfair
    8636,  // unfold
    8641,  // unhappy
    8646,  // union
    8648,  // universe
    8654,  // unkind
    8656,  // unknown
    8687,  // unusual
    8697,  // unwrap
    8647,  // upgrade
    8678,  // upstairs
    8737,  // username
    8743,  // usher
    8781,  // usual
    8154,  // valid
    8158,  // valuable
    8156,  // vampire
    8164,  // vanish
    8174,  // various
    8341,  // vegan
    8358,  // velvet
    8368,  // venture
    8372,  // verdict
    8374,  // verify
    8379,  // very
    8383,  // veteran
    8393,  // vexed
    8428,  // victim
    8423,  // video
    8439,  // view
    8468,  // vintage
    8465,  // violence
    8471,  // viral
    8474,  // visitor
    8478,  // visual
    8481,  // vitamins
    8621,  // vocal
    8642,  // voice
    8658,  // volume
    8683,  // voter
    8684,  // voting
    9156,  // walnut
    9175,  // warmth
    9176,  // warn
    9182,  // watch
    9189,  // wavy
    9315,  // wealthy
    9316,  // weapon
    9312,  // webcam
    9352,  // welcome
    9353,  // welfare
    9378,  // western
    9428,  // width
    9452,  // wildlife
    9462,  // window
    9463,  // wine
    9473,  // wireless
    9472,  // wisdom
    9484,  // withdraw
    9487,  // wits
    9653,  // wolf
    9651,  // woman
    9675,  // work
    9678,  // worthy
    9716,  // wrap
    9747,  // wrist
    9748,  // writing
    9768,  // wrote
    9317,  // year
    9356,  // yelp
    9435,  // yield
    9641,  // yoga
    9376,  // zero
};
