import re
import pandas as pd
from typing import Optional, List
from pandarallel import pandarallel
from typing import Optional, List

class ViolencePatternMatcher:
    def __init__(self):
        # Define gap patterns
        self.larger_gap = r"[^\.]{0,35}"
        self.large_gap = r"[^\.]{0,25}"
        self.medium_gap = r"[^\.]{0,15}"
        self.small_gap = r"[^\.]{0,10}"
        self.end_gap = r"[^.]*\."     
        self.start_gap = r"\.[^.]*"    

        # Build patterns
        self._build_confounding_patterns()
        self._build_violence_patterns()
        
        # Compile regex patterns
        self.confounding_re = re.compile(self.confounding_all)
        self.violence_re = re.compile(self.violence_patterns)

    def _build_confounding_patterns(self):
        """Build all confounding patterns that should be excluded"""
        policeforces = r"(police|security (personnel|forces|services)|officials|authorities)"

        self.noreports = "no" + self.small_gap + r"(reports|security-related)" + self.small_gap + r"(clashes|arrests|police intervention|violence|incidents)"
        self.inyear = self.start_gap + r" in " + self.medium_gap + r"\d{4}(?!hrs)" + self.end_gap
        self.ondateyear = self.start_gap + r" on \d{2} " + self.medium_gap + r"\d{4}(?!hrs)" + self.end_gap
        self.earlierthis = self.start_gap + r"earlier this year" + self.end_gap
        self.lastyear = r"\. last year" + self.end_gap
        self.inrecentyears = self.start_gap + r"in recent years" + self.end_gap
        self.onlyoccasional = self.start_gap + r"only occasionally" + self.end_gap
        self.likelydisperse = "likely to " + r"(disperse|suppress)" + self.end_gap
        self.severalofthese = "it should be " + r"(further )?noted that several of these" + self.end_gap
        self.incidental = self.start_gap + r"incidental" + self.medium_gap + r"violence" + self.end_gap
        self.mayuseforce = "may use " + r"(excessive )?force" + self.end_gap
        self.pastactions = self.start_gap + r"(previous|past) " + self.medium_gap + r"(protests|demonstrations|rallies|marches)" + self.end_gap
        self.propensitytoturn = r"(propensity to|may) turn violent" + self.end_gap
        self.knowntoattack = "have been known to " + r"(block|attack)" + self.end_gap
        self.heightened = "heightened potential for " + self.end_gap
        self.escalateinto = "potential to escalate into" + self.end_gap
        self.generallypeaceful = r"(generally|usually) (been )?peaceful" + self.end_gap
        self.levelofyear = self.start_gap + r"level of \d{4}" + self.end_gap
        self.variousoccasions = r"\. there have been various occasions" + self.end_gap
        self.sporadically = "sporadically escalated" + self.end_gap
        self.possibilityof = r"\. the possibility of further" + self.end_gap
        self.rarelyresult = "rarely result in" + self.end_gap
        self.personnelshould = "personnel should" + self.end_gap
        self.likelycontinue = self.start_gap + r"will likely continue"
        self.likelybepeaceful = "likely (to )?be peaceful" + self.end_gap
        self.clashespossible = r"(clashes|crackdowns|confrontations) (between)?( protest)?" + self.medium_gap + r" are (possible|likely)" + self.end_gap
        self.clashesmay = r"(clashes|crackdowns|confrontations) (may|can|could|might) " + self.end_gap
        self.likelytobe = "likely to be dispersed" + self.end_gap
        self.potentialclash = r"(potential|possible|likely)( of)? clash" + self.end_gap
        self.noclashes = "no clash" + self.end_gap
        self.couldinvolve = "could involve" + self.end_gap
        self.preparefor = "prepare for (increased|heightened) security" + self.end_gap
        self.exercisecaut = "exercisecaution" + self.end_gap
        self.almostcertain = "almost certain" + self.end_gap
        self.likelyuse = r"(likely|might|can|could) use force" + self.end_gap
        self.mayuselethal = "may use( lethal)? force" + self.end_gap
        self.arealsopossible = self.start_gap + r"are( also)? possible"
        self.couldoccur = self.start_gap + r"(could|may) occur"
        self.likelyattempt = "likely attempt" + self.end_gap
        self.betweenpossible = r"clashes between protest" + self.medium_gap + r"are (possible|likely)" + self.end_gap
        self.policetypically = policeforces + r" typically" + self.end_gap
        self.particularlyif = "particularly (if|should) " + policeforces + self.end_gap
        self.policewilllikely = policeforces + r" will (likely|possibly|probably)" + self.end_gap
        self.policemay = policeforces + r" (may|could|can)" + self.end_gap
        self.notberuledout = self.start_gap + r"not be ruled out"
        self.comingweeks = self.start_gap + r"in the coming weeks"
        self.mainlyifpolice = "mainly if " + policeforces + self.end_gap
        self.mainlyifpolice_st = self.start_gap + "mainly if " + policeforces
        self.thoseplanning = "those planning to" + self.end_gap
        self.couldresultin = "could result in" + self.end_gap
        self.areunlikely = self.start_gap + "are unlikely."
        self.maymaterialize = self.start_gap + "may materialize"
        self.mayclash = "may clash with" + self.end_gap
        self.especiallyif = "especially if" + self.end_gap
        self.ifpoliceforcibly = "if " + policeforces + " forcibly" + self.end_gap
        self.heightenedrisk = "heightened risk of" + self.end_gap
        self.policearepossible = self.start_gap + policeforces + " are (likely|possible)"
        self.couldresort = r"(may|can|could) resort to" + self.end_gap
        self.noreported = " no report incident" + self.end_gap
        self.clasheslikely = "clashes between" + self.medium_gap + r"are (likely|possible)"
        self.possibilityof = "possibility of " + self.medium_gap
        self.previousceleb = "previous celebrations" + self.end_gap
        self.arelikelyto = "are likely to react" + self.end_gap
        self.rivalsecurity = self.start_gap + "between rival security"
        self.arrestofsuspect = r"(arrest|detain)" + self.medium_gap + "suspect"
        self.suspectarrest = "suspect" + self.medium_gap + r"(arrest|detain)"
        self.oftenturn = "often turn violent" + self.end_gap
        self.travelhazardous = self.start_gap + "travel hazardous"
        self.highpropensity = "high propensity to" + self.end_gap
        self.delaystotravel = self.start_gap + "delays to travel"
        self.elevatedthreat = r"(elevated)? threat( of)?" + self.end_gap
        self.itislikely = "it is( highly)? (likely|possible)" + self.end_gap
        self.couldelicit = r"(might|can|could|may) elicit" + self.end_gap
        self.bomb = r"(the blast|explosion|bomb)" + self.end_gap

        self.confounding_all = "|".join([
            self.noreports, self.inyear, self.ondateyear, self.earlierthis,
            self.lastyear, self.variousoccasions, self.escalateinto,
            self.inrecentyears, self.onlyoccasional, self.likelydisperse,
            self.severalofthese, self.incidental, self.rarelyresult,
            self.mayuseforce, self.pastactions, self.propensitytoturn,
            self.knowntoattack, self.heightened, self.generallypeaceful,
            self.levelofyear, self.sporadically, self.possibilityof,
            self.personnelshould, self.likelycontinue,
            self.likelybepeaceful, self.clashespossible, self.likelytobe,
            self.potentialclash, self.noclashes, self.couldinvolve,
            self.preparefor, self.exercisecaut, self.almostcertain,
            self.likelyuse, self.mayuselethal, self.arealsopossible,
            self.couldoccur, self.likelyattempt, self.betweenpossible,
            self.policetypically, self.policemay, self.particularlyif,
            self.policewilllikely, self.notberuledout,
            self.comingweeks, self.mainlyifpolice, self.mainlyifpolice_st,
            self.thoseplanning, self.couldresultin, self.areunlikely,
            self.maymaterialize, self.mayclash, self.ifpoliceforcibly,
            self.especiallyif, self.heightenedrisk, self.couldresort,
            self.policearepossible, self.noreported, self.previousceleb,
            self.clasheslikely, self.possibilityof, self.arelikelyto,
            self.rivalsecurity, self.arrestofsuspect, self.oftenturn,
            self.travelhazardous, self.highpropensity, self.delaystotravel,
            self.elevatedthreat, self.itislikely, self.couldelicit, self.clashesmay,
            self.suspectarrest, self.bomb
        ])

    def _build_violence_patterns(self):
        """Build patterns that indicate actual violence/suppression"""
        police = r"(police|security|law enforcement (officials|officers))"

        police_equipment = "|".join([
            "tear gas",
            "water cannon",
            "baton",
            "live (ammunition|rounds)",
            "pepper spray",
            "rubber bullet",
            "electroshock weapon",
            r"(flash|concussion|stun)[^.]{0,3}(bang|grenade)"
        ])

        protester = r"protest[eo]r"
        demonstrator = "demonstrator"
        activist = "activist"
        supporter = "supporter"
        worker = "worker"
        people_word = "people"
        residents = r"(?<!p)resident"
        students = "student"
        youth = "youth"
        teacher = "teacher"
        farmer = "farmer"
        villager = "villager"
        lawyer = "lawyer"
        separatists = "separatist"
        members = "member"
        migrants = "migrant"
        women = "women"
        participants = "participant"
        miner = "miner"
        bypolice = self.small_gap + police
        rioter = "rioter"
        crowd = "crowd"

        actors = "|".join([
            protester, demonstrator, activist, supporter, worker,
            people_word, residents, students, youth, teacher, farmer,
            villager, lawyer, separatists, members, migrants,
            women, participants, miner, people_word, crowd
        ])
        actors_extended = actors + "|" + bypolice

        arrest = r"(arrest|detain)"
        protest = r"(?<!by )protest"
        demonstration = "demonstration"
        rally = r"rall(y|ies)"
        riot = r"(?<!by )riot"
        march = "march"
        gathering = "gathering"
        sitin = r"sit[^.]{0,3}in"

        actions = "|".join([protest, demonstration, rally, riot, march, gathering, sitin])

        stone_police = r"(stone|rock|brick|projectile)" + self.medium_gap + "at" + self.small_gap + police
        running_battle = "running battle"
        disperse_first = "disperse" + self.large_gap + "(" + actors_extended + "|" + actions + ")"
        break_up = "(break|broke) up" + self.medium_gap + "(" + actions + ")"
        clash_police = "(clash|scuffle)" + self.medium_gap + "(between)?" + self.medium_gap + police
        police_clash = police + self.large_gap + "(clash|scuffle)"
        arrested_actor = arrest + self.large_gap + "(" + (actors + "|person(?!nel)") + ")"
        actor_arrested = "(" + (actors + "|person(?!nel)") + ")" + self.large_gap + arrest
        arrested_number = arrest + self.large_gap + r"\d{1,4}(?! on )(?! between)"
        number_arrested = r"(?<!on )(?<!between )\d{1,4}" + self.large_gap + arrest
        arrested_dozens = arrest + self.large_gap + r"(dozens|tens|hundreds|thousands)"
        dozens_arrested = r"(dozens|tens|hundreds|thousands)" + self.medium_gap + arrest
        opened_fire = police + self.small_gap + "opened fire"
        brutality_1 = police + self.small_gap + "brutality"
        brutality_2 = "brutality" + self.small_gap + police
        injured_1 = "injured" + self.medium_gap + police
        injured_2 = police + self.medium_gap + "injured"
        crackdown_1 = police + self.large_gap + "crackdown"
        crackdown_2 = "crackdown" + self.large_gap + police
        crackdown_3 = "crackdown" + self.large_gap + "(" + actors + "|" + actions + ")"
        crackdown_4 = "(" + actors + "|" + actions + ")" + self.large_gap + "crackdown"
        crackdown_5 = "government" + self.large_gap + "crackdown"
        confront_police = "confront" + self.medium_gap + police
        confront_long = "confront" + self.small_gap + "between" + "(" + actors + ")" + self.medium_gap + police
        prevented_1 = police + self.medium_gap + "(prevent|block)" + self.medium_gap + "(" + actions + ")"
        prevented_2 = "(" + actions + ")" + self.medium_gap + "(prevent|block)" + self.medium_gap + police
        disbanded = "disbanded" + self.medium_gap + police
        actorsattack = "(" + actors + ")" + self.medium_gap + "attack" + self.medium_gap + police

        self.violence_patterns = "|".join([
            police_equipment, stone_police, running_battle,
            disperse_first, break_up, clash_police, police_clash,
            arrested_actor, actor_arrested, arrested_number,
            number_arrested, opened_fire, brutality_1,
            brutality_2, crackdown_1, crackdown_2, crackdown_3,
            crackdown_4, crackdown_5, confront_long,
            confront_police, prevented_1, prevented_2,
            injured_1, injured_2, disbanded, actorsattack,
            arrested_dozens, dozens_arrested
        ])

    def parse_text(self, text: str) -> int:
        """
        Analyze text for violence/suppression patterns.
        Returns 1 if violence patterns found (after removing confounding patterns), 0 otherwise.
        """
        if not text:
            return 0
            
        # First remove confounding patterns
        clean_text = self.confounding_re.sub("", text)
        
        # Then search for violence patterns
        if self.violence_re.search(clean_text):
            return 1
        return 0

class OSACSuppressionParser:
    def __init__(self, patterns: Optional[List[str]] = None):
        # Use only the specified patterns
        self.violence_matcher = ViolencePatternMatcher()

    def parse_suppression(self, 
                     title: Optional[str] = None,
                     location: Optional[str] = None,
                     events: Optional[str] = None,
                     actions: Optional[str] = None,
                     assistance: Optional[str] = None,
                     other: Optional[str] = None) -> int:
        # Convert all inputs to strings, handling None and NaN values
        title = str(title) if pd.notna(title) else ""
        location = str(location) if pd.notna(location) else ""
        events = str(events) if pd.notna(events) else ""
        actions = str(actions) if pd.notna(actions) else ""
        assistance = str(assistance) if pd.notna(assistance) else ""
        other = str(other) if pd.notna(other) else ""
        
        text = " ".join([title, location, events, actions, assistance, other])
        
        violence_result = self.violence_matcher.parse_text(text)
        return violence_result
class OSACSuppressionProcessor(OSACSuppressionParser):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        pandarallel.initialize()
        self.df = df.copy()
        self.df.columns = self.df.columns.str.strip()
        
        # Convert all relevant columns to strings, replacing NaN with empty string
        text_cols = ['OSAC_Title', 'OSAC_Location', 'OSAC_Events', 
                    'OSAC_Actions', 'OSAC_Assistance', 'OSAC_Other']
        for col in text_cols:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).replace('nan', '')
    
    @property
    def extract(self) -> pd.DataFrame:
        if 'suppression' not in self.df.columns:
            self.df['suppression'] = None
            
        needs_processing = self.df['suppression'].isna() | (self.df['suppression'] == '')
        
        if needs_processing.any():
            # Parallel apply for processing
            self.df.loc[needs_processing, 'suppression'] = (
                self.df.loc[needs_processing]
                .parallel_apply(
                    lambda row: self.parse_suppression(row['OSAC_Title'],
                                                row['OSAC_Location'],
                                                row['OSAC_Events'],
                                                row['OSAC_Actions'],
                                                row['OSAC_Assistance'],
                                                row['OSAC_Other']),
                    axis=1
                )
            )
        
        return self.df

if __name__ == "__main__":
    pass