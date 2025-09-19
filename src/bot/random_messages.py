"""
Random appendix messages for fishing notifications.
Contains humorous messages that are randomly appended to cast and hook notifications in groups.
"""

import random

# Random appendix messages for cast notifications
CAST_APPENDIX_MESSAGES = [
    " Time to lose money with style and panache.",
    " Because who needs financial stability anyway.",
    " Another brave soul enters the hunger games.",
    " The market gods demand a sacrifice.",
    " Probability of success: 42% (or was it 24%?).",
    " Warning: may contain traces of devastating losses.",
    " Another portfolio's funeral begins now.",
    " The casino is officially open for business.",
    " Today's forecast: 90% chance of getting rekt.",
    " Don't panic - that comes later.",
    " Side effects may include chronic optimism.",
    " Terms and conditions: probably won't be read anyway.",
    " Narrator: they did not, in fact, catch anything good.",
    " The definition of insanity starts here.",
    " Future self is already disappointed.",
    " Welcome to the machine that goes 'ping' and empties wallets.",
    " Caution: fishing rod may be smarter than operator.",
    " The improbability drive is fully charged.",
    " Another volunteer for the economic experiment.",
    " Murphy's Law is particularly active today.",
    " The fish have unionized and demand better working conditions.",
    " Warning: this pond may contain interdimensional parasites.",
    " Fishing license has been revoked by the Department of Bad Decisions.",
    " The fish are currently holding a conference about this trading strategy.",
    " Schrödinger's fish: simultaneously caught and escaped until observed.",
    " The pond's AI has achieved sentience and judges life choices.",
    " The fishing rod is experiencing an existential crisis.",
    " The water temperature is optimal for regret cultivation.",
    " Local fish report: 'humans still haven't learned'.",
    " The fishing gods are currently on their lunch break.",
    " The bait smells suspiciously like desperation.",
    " The fish have installed ad-blockers against hooks.",
    " Warning: pond may contain traces of broken dreams and student loans.",
    " The local fish population has started a betting pool on this failure.",
    " This fishing technique has been classified as a war crime in 12 jurisdictions.",
    " The pond's customer service department is permanently closed.",
    " Fish advisory: humans detected, initiating evasion protocol.",
    " Optimism level exceeds recommended daily allowance.",
    " The fish have formed a support group for trauma recovery.",
    " Caution: fishing may cause spontaneous financial advice from strangers.",
    " The pond's terms of service were written by Kafka.",
    " Fishing karma balance is currently -42 points.",
    " The fish are livestreaming these attempts on FishTok.",
    " Warning: may cause temporary belief in one's own competence.",
    " The water has been blessed by the patron saint of poor decisions."
]

# Random appendix messages for hook notifications (third person)
HOOK_APPENDIX_MESSAGES = [
    " The fish didn't see that coming.",
    " Another victim of capitalist fishing.",
    " The pond's ecosystem is officially disturbed.",
    " Their rod has achieved temporary competence.",
    " The fish's retirement plan just got cancelled.",
    " Market manipulation at its finest.",
    " The fishing gods temporarily glitched.",
    " Their luck buffer has been depleted by 73%.",
    " The fish filed a complaint with management.",
    " Statistical anomaly detected and exploited.",
    " The pond's error 404: fish not found.",
    " Their fishing algorithm briefly achieved consciousness.",
    " The fish's insurance claim was denied.",
    " Murphy's Law took a coffee break.",
    " The pond's quantum mechanics are malfunctioning.",
    " Their competence levels are dangerously high.",
    " The fish's existential crisis reached critical mass.",
    " Market forces temporarily aligned with their delusions.",
    " The fishing matrix has been successfully hacked.",
    " Their rod's warranty just expired from overperformance.",
    " The fish's GPS system was obviously broken.",
    " Their fishing karma debt has been temporarily forgiven.",
    " The pond's difficulty setting was accidentally lowered.",
    " The fish mistook their hook for a mortgage application.",
    " Their trading bot achieved sentience for 0.3 seconds.",
    " The fish's legal team is preparing a countersuit.",
    " Their luck subscription has been mysteriously renewed.",
    " The pond's terms of service were clearly not read.",
    " The fish's union representative was on vacation.",
    " Their fishing technique violated several laws of physics.",
    " The market's random number generator is clearly rigged.",
    " The fish's protest march was poorly organized.",
    " Their rod's AI achieved temporary enlightenment.",
    " The pond's customer support system crashed.",
    " The fish's escape plan had a critical bug.",
    " Their fishing license was upgraded without consent.",
    " The pond's security system experienced a buffer overflow.",
    " The fish's revolutionary movement has been suppressed.",
    " Their competence firewall has been temporarily disabled.",
    " The fishing gods' quality control department is clearly understaffed."
]

def get_random_cast_appendix() -> str:
    """Get a random cast appendix message."""
    return random.choice(CAST_APPENDIX_MESSAGES)

def get_random_hook_appendix() -> str:
    """Get a random hook appendix message."""
    return random.choice(HOOK_APPENDIX_MESSAGES)