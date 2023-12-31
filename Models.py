from pydantic import BaseModel
from typing import Optional, Any


class Match(BaseModel):
    id: int
    md: str
    ht: str
    ht_id: int
    ht_abbr: str
    ht_slug: str
    ht_slug_en: str
    at: str
    at_id: int
    at_abbr: str
    at_slug: str
    at_slug_en: str
    uri: str
    inplay: int
    current_time: int
    additional_time: str
    hscore: Any
    ascore: Any
    status: Any
    matchstatus: int
    popular: str
    cancel: str
    special_status: Any
    status_reason: Any
    sport_id: int
    category_id: int
    league_id: int
    sport_sort: int
    league_sort: Optional[int]
    game_score: Any
    inplay_status: Any
    show_inplay_status: bool
    postmatch_status: Any
    halftime: Any
    ht_red_cards: int
    at_red_cards: int
    winner: Any
    aggregate_winner: int
    league_round_name: Optional[str]
    has_limited_coverage: bool
    aggregate_home_score: Optional[str]
    aggregate_away_score: Optional[str]
    group_name: str
    has_special_offer: Any



class LastMatch(BaseModel):
    id: int
    md: str
    ht: str
    ht_id: int
    ht_abbr: str
    ht_slug: str
    at: str
    at_id: int
    at_abbr: str
    at_slug: str
    uri: str
    current_time: int
    additional_time: str
    hscore: Optional[int]
    ascore: Optional[int]
    status: Optional[str]
    matchstatus: int
    special_status: int
    status_reason: Optional[str]
    winner: Optional[int]
    inplay_status: Optional[str]
    show_inplay_status: bool
    postmatch_status: Optional[str]
    halftime: Optional[str]
    outcome: str
    league_id: int
    has_limited_coverage: bool
    home: bool