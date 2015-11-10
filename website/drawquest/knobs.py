REWARDS = {
    'star': 0,
    'first_quest': 25,
    'quest_of_the_day': 5,
    'archived_quest': 1,
    'personal_share': 3,
    'personal_twitter_share': 3,
    'streak_3': 3,
    'streak_10': 10,
    'streak_100': 100,
    'featured_in_explore': 10,
}

ONBOARDING_QUEST_ID = 926

QUESTS_PER_PAGE = 40
COMMENTS_PER_PAGE = 50
FOLLOWERS_PER_PAGE = 100

QUEST_INBOX_SIZE = 50
QUEST_HISTORY_SIZE = 50
TOP_QUESTS_SIZE = 150
TOP_GALLERY_SIZE = 100

TOP_GALLERY_SIZE_BEFORE_CACHING = 5

WHITELIST_COMMENTS_PER_PAGE = 1000

EXPLORE_BUCKET_SIZE = 33
EXPLORE_DISPLAY_SIZE = 20
EXPLORE_ROLLOVER_HOUR = 13 # UTC

SEARCH_RESULTS_PER_PAGE = 40

AUTO_MODERATION = {
    'followers': 10,
    'stars': 5,
}

CURRENT_APP_VERSION = '3.0'

APP_LOG_FLUSH_MIN_TIME    = 60*5
APP_LOG_FLUSH_MAX_RECORDS = 50

COLOR_CHECKMARK_LUMINOSITY_THRESHOLD = 0.5

# Per trust level: None=Unknown, False=Distrusted, True=Trusted.
AUTO_DISABLE_FLAGGED_COMMENTS_THRESHOLD = {
    None:  3,
    False: 3,
    True:  4,
}
AUTO_CURATE_FLAGGED_COMMENTS_THRESHOLD = {
    None:  1,
    False: 1,
    True:  3,
}

# Thanks google.
FLAG_WORDS = ['dick', 'penis', 'ass', 'butts', 'cock', 'cocks', 'asses', 'shit', 'nig', 'sex', 'murder', 'suicide', 'piss', 'goddamn', 'pussy', 'vagina', 'nazi', 'nazis', 'penises', 'whore', 'bitch', 'b1tch', 'butt', 'poop', 'jew', 'jews', 'jewry', 'hasid', 'fag', 'fags', 'faggy', 'retard', 'bastard', 'arse', 'bastards', 'bitches', 'bitchin', 'boob', 'boobs', 'breasts', 'breast', 'cum', 'cunt', 'cunts', 'dildo', 'douche', 'fanny', 'fcuk', 'fukk', 'felch', 'gaylord', 'goatse', 'gangbang', 'homo', 'homos', 'jap', 'spic', 'spics', 'japs', 'mofo', 'm0fo', 'm0f0', 'nigga', 'n1gga', 'nigg3r', 'porn', 'p0rn', 'pr0n', 'pron', 'numbnuts', 'orgasm', 'orgasim', 'rectum', 'rectal', 'pube', 'pubes', 'porno', 'pornography', 'pornos', 'pusse', 'pussi', 'prick', 'pricks', 'rimming', 's hit', 'sadist', 'scrote', 'scrotum', 'scrotal', 'semen', 'shag', 'shagging', 'shags', 'shagged', 'dicks', 'dickhead', 'dickheads', 'd1ck', 'd1cks', 'dikky', 'dikk', 'd1kk', 'shits', 'slut', 'sluts', 'whores', 'smemgma', 'smut', 'skank', 'skanky', 'skanks', 'snatch', 'spunk', 'tit', 'tits', 't1ts', 'titty', 'titties', 'twat', 'twats', 'twathead', 'wank', 'wanker', 'wankers', 'wanking', 'wanked', 'turd', 'terd', 'turds', 'anal', 'twatty', 'viagra', 'boner', 'boners', 'erection', 'stiffy', 'wang', 'wangs', 'willies', 'xxx', 'xrated', 'teet', 'teets', 'shitting', 'shitty', 'jerk-off', 'jerkoff', 'horny', 'horniest', 'hotsex', 'hore', 'fudgepacker', 'fux', 'fuxor', 'fux0r', 'gaysex', 'f4nny', 'doggin', 'dogging', 'dyke', 'dykes', 'doosh', 'crap', 'drugs', 'drugged', 'drunk', 'alcohol', 'chink', 'chinks', 'chinky', 'clit', 'clitoris', 'clits', 'bloody', 'bleeding', 'bestial', 'beastial', 'bestiality', 'beastiality', 'boners', 'fat-ass', 'fudge packer', 'fudge pack', 'labia', 'numbnuts', 'nutsack', 'pecker', 'phuk', 'phuck', 'phukking', 'phukked', 'phucked', 'phukker', 'phuker', 'phucker', 'phukkers', 'phuq', 'pisser', 'pissing', 'peeing', 'pooping', 'rimming', 'shemale', 'tranny', 'trannies', 'tittie5', 'twunt', 'murdered', 'murdering', 'assed', 'feck', 'f u c k', 'fagot', 'fagots', 'fanyy', 'fook', 'fooking', 'kawk', 'kum', 'kums', 'batin', 'baitin', 'mo-fo', 'mo fo', 'nob', 'nazis', 'nobhead', 'pimp', 'pimpin', 'pimping', 'pimped', 'p1mp', 'pimper', 'pimps', 'pimpz', 'p1mps', 'shlong', 'scroat', 'screwing', 'shiting', 'shite', 'vulva', 'hump', 'humping', 'perv', 'pervy', 'pervin', 'pervert', 'perving', 'sexing', 'sext', 'sexting', 'sexts', 'sexted', 'a-hole', 'taint', 'nipple', 'nipples']
FLAG_WORD_FRAGMENTS = ['fuck', 'nigger', 'n1gg', 'hitler', 'faggot', 'bollock', 'blowjob', 'handjob', 'asshole', 'c0ck', 'douchebag', 'jizz', 'masturbat', 'masterbat', 'niggah', 'phonesex', 'cybersex', 'shitter', 'shithead', 'testicle', 'testical', 'testicular', 'fatass', 'rimjob', 'cocksuck', 'cocksuk', 'cokehead', 'cocaine', 'ch1nk', 'ballsack', 'b00b', 'a55', '4r5e', '5hit', 'a_s_s', 'fukwit', 'jizm', 'f_u_c_k', 'nignog', 'n1gn0g', 'ejakulat', 'm45terb', 'm45turb', 'assmunch', 'cockmunch', 'foreskin', 'prostitut', 'nympho']

