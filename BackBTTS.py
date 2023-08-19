import datetime
from playwright.sync_api import sync_playwright
from Models import Match, LastMatch
from fastapi.encoders import jsonable_encoder
import pandas as pd
import smtplib
import email


def main():
    url = 'https://www.oddspedia.com/'
    ua = (
        "Mozilla/5.0 (Windows NT 24.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/69.0.3497.240 Safari/537.36"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=ua)
        page.goto(url)
        page.wait_for_timeout(1000)
        today_date = datetime.date.today()
        # today_date = "2023-04-15"
        tomorrow_date = today_date + datetime.timedelta(days=1)
        # tomorrow_date = "2023-04-16"
        api_url = f"https://oddspedia.com/api/v1/getMatchList?excludeSpecialStatus=0&sortBy=default&perPageDefault=1000&startDate={today_date}T06%3A00%3A00Z&endDate={tomorrow_date}T05%3A59%3A59Z&geoCode=PT&status=all&sport=football&popularLeaguesOnly=0&page=1&perPage=1000&language=en"
        data = page.goto(api_url).json()

        df = get_match_df(data)

        df['ht_form'] = ""
        df['at_form'] = ""
        df['home_odd'] = 0
        df['draw_odd'] = 0
        df['away_odd'] = 0

        for index, row in df.iterrows():
            (home_odd, draw_odd, away_odd) = get_match_odds(page, row['id'])
            df.at[index, 'home_odd'] = home_odd
            df.at[index, 'draw_odd'] = draw_odd
            df.at[index, 'away_odd'] = away_odd

        df.set_index(inplace=True, keys=['id'])
        # df['league_round_name'] = df.apply(lambda row: row.league_round_name[-2:], axis=1)
        # df = df.astype({'league_round_name': 'int'})
        df['home_perc_over_1'] = 0
        df['away_perc_over_1'] = 0
        df['home_perc_over_2'] = 0
        df['away_perc_over_2'] = 0
        df['ht_form'] = ""
        df['at_form'] = ""
        df['percentage_home_btts_matches'] = 0
        df['percentage_away_btts_matches'] = 0
        df['btts_yes_odd'] = 0
        df['btts_no_odd'] = 0

        insert_home_and_away_form(page, df)

        df['btts_match_teams_avrg'] = df.apply(lambda row: (row.percentage_home_btts_matches + row.percentage_away_btts_matches) / 2, axis=1)
        df['over_1_match_teams_avrg'] = df.apply(lambda row: (row.home_perc_over_1 + row.away_perc_over_1) / 2, axis=1)
        df['over_2_match_teams_avrg'] = df.apply(lambda row: (row.home_perc_over_2 + row.away_perc_over_2) / 2, axis=1)
        df['bet'] = False
        # df = df.query('ht_form.str.len() >= 3 & at_form.str.len() >= 3 &btts_match_teams_avrg > 0.60 & over_1_match_teams_avrg > 0.70 & over_2_match_teams_avrg > 0.45')
        # df = df.query('ht_form.str.len() >= 3 & at_form.str.len() >= 3 &btts_match_teams_avrg > 0.55 & over_1_match_teams_avrg > 0.55 & over_2_match_teams_avrg > 0.55')
        df = df.query('ht_form.str.len() >= 3 & at_form.str.len() >= 3')

        check_if_bet(df)

        final_df = df.sort_values(by="md", ascending=True).query('bet == True')
        print(final_df.to_string())
        send_email(final_df)

def check_if_bet(df):
    league_querys = {
        4 : ["50_60_55"],    # Germany Bundesliga
        46: ["65_80_40"],   # Germany Bundesliga 2
        24: ["55_60_40"],   # France Ligue 1
        838:["60_65_45", "55_70_45"],  # France Ligue 2
        627:["25_75_70"],  # England Premier League
        15: ["55_95_5"],   # England Championship
        47: ["0_70_45"],   # Portugal Primeira Liga
        889:["55_65_45"],  # Portugal Segunda Liga
        86: ["40_70_60"],   # Switzerland Super League
        31: ["55_60_35"],   # Italy Serie A
        34: ["50_90_45"],   # Italy Serie B
        2:  ["60_65_40"],    # Spain Primera Division
        64: ["50_60_25"]    # Spain Segunda Division
    }
    for index, row in df.iterrows():
        league_id = row['league_id']
        for league_query in league_querys[league_id]:
            (b, o, t) = map(int, league_query.split(sep='_'))
            if row['btts_match_teams_avrg'] >= b/100 and row['over_1_match_teams_avrg'] >= o/100 and row['over_2_match_teams_avrg'] >= t/100:
                df.at[index, 'bet'] = True


def get_match_df(matches):
    league_ids = [
        4,    # Germany Bundesliga
        46,   # Germany Bundesliga 2
        24,   # France Ligue 1
        838,  # France Ligue 2
        627,  # England Premier League
        15,   # England Championship
        47,   # Portugal Primeira Liga
        889,  # Portugal Segunda Liga
        86,   # Switzerland Super League
        31,   # Italy Serie A
        34,   # Italy Serie B
        2,    # Spain Primera Division
        64    # Spain Segunda Division
    ]

    json_matchlist = matches['data']['matchList']
    # matches = [Match(**match) for match in json_matchlist if (match['matchstatus'] == 8 and match['league_id'] in league_ids)]
    matches = [Match(**match) for match in json_matchlist if (match['matchstatus'] == 1 and match['league_id'] in league_ids)]
    return pd.DataFrame(jsonable_encoder(matches))

def get_match_odds(page, match_id):
    odds_url = f"https://oddspedia.com/api/v1/getMatchOdds?wettsteuer=0&geoCode=PT&bookmakerGeoCode=PT&bookmakerGeoState=&matchId={match_id}&language=en"
    odds_json = page.goto(odds_url).json()

    full_time_period_odds = next(
        odd['periods'] for odd in odds_json['data']['prematch'] if odd['name'] == 'Full Time Result')
    full_time_odds = next(odd['odds'] for odd in full_time_period_odds if odd['name'] == 'Full Time')
    try:
        betclic_full_time_odds = next(odd for odd in full_time_odds if odd['bookie_name'] == 'Betclic')
    except StopIteration:
        betclic_full_time_odds = next(odd for odd in full_time_odds if odd['bookie_name'] == 'Bwin')
    return betclic_full_time_odds['o1'], betclic_full_time_odds['o2'], betclic_full_time_odds['o3']


def insert_home_and_away_form(page, df):
    for index, row in df.iterrows():
        # sleep(0.05)
        match_date = row['md']
        league_id = row['league_id']
        home_team_id = row['ht_id']
        away_team_id = row['at_id']

        raw_home_team_last_matches = get_last_match_df(page, league_id, home_team_id)
        raw_away_team_last_matches = get_last_match_df(page, league_id, away_team_id)

        if not raw_home_team_last_matches.empty and not raw_away_team_last_matches.empty:
            home_team_last_matches = raw_home_team_last_matches.sort_values(by='md', ascending=False).query(
                'ht_id == @home_team_id & md < @match_date')
            away_team_last_matches = raw_away_team_last_matches.sort_values(by='md', ascending=False).query(
                'at_id == @away_team_id & md < @match_date')

            home_team_form = "".join(home_team_last_matches['outcome'].head().values)
            away_team_form = "".join(away_team_last_matches['outcome'].head().values)

            df.at[index, 'ht_form'] = home_team_form
            df.at[index, 'at_form'] = away_team_form

            home_team_season_last_matches = home_team_last_matches
            away_team_season_last_matches = away_team_last_matches

            home_team_btts_df = home_team_season_last_matches.query("hscore > 0 & ascore > 0")
            away_team_btts_df = away_team_season_last_matches.query("hscore > 0 & ascore > 0")

            home_team_over1_df = home_team_season_last_matches.query("(hscore + ascore) > 1.5")
            away_team_over1_df = away_team_season_last_matches.query("(hscore + ascore) > 1.5")

            home_team_over2_df = home_team_season_last_matches.query("(hscore + ascore) > 2.5")
            away_team_over2_df = away_team_season_last_matches.query("(hscore + ascore) > 2.5")

            if not home_team_season_last_matches.empty:
                df.at[index, 'percentage_home_btts_matches'] = len(home_team_btts_df) / len(home_team_season_last_matches)
                df.at[index, 'home_perc_over_1'] = len(home_team_over1_df) / len(home_team_season_last_matches)
                df.at[index, 'home_perc_over_2'] = len(home_team_over2_df) / len(home_team_season_last_matches)

            if not away_team_season_last_matches.empty:
                df.at[index, 'percentage_away_btts_matches'] = len(away_team_btts_df) / len(away_team_season_last_matches)
                df.at[index, 'away_perc_over_1'] = len(away_team_over1_df) / len(away_team_season_last_matches)
                df.at[index, 'away_perc_over_2'] = len(away_team_over2_df) / len(away_team_season_last_matches)

        (btts_yes_odd, btts_no_odd) = get_match_btts_odds(page, index)
        df.at[index, 'btts_yes_odd'] = btts_yes_odd
        df.at[index, 'btts_no_odd'] = btts_no_odd


def get_match_btts_odds(page, match_id):
    odds_url = f"https://oddspedia.com/api/v1/getMatchOdds?wettsteuer=0&geoCode=PT&bookmakerGeoCode=PT&bookmakerGeoState=&matchId={match_id}&oddGroupId=11&inplay=0&language=en"
    odds_json = page.goto(odds_url).json()

    try:
        both_teams_to_score_odds = next(odd['periods'] for odd in odds_json['data']['prematch'] if odd['name'] == 'Both Teams to Score')
        full_time_odds = next(odd['odds'] for odd in both_teams_to_score_odds if odd['name'] == 'Full Time')
        betclic_full_time_odds = next(odd for odd in full_time_odds if odd['bookie_name'] == 'Betway')
    except StopIteration:
        try:
            both_teams_to_score_odds = next(odd['periods'] for odd in odds_json['data']['prematch'] if odd['name'] == 'Both Teams to Score')
            full_time_odds = next(odd['odds'] for odd in both_teams_to_score_odds if odd['name'] == 'Full Time')
            betclic_full_time_odds = next(odd for odd in full_time_odds if odd['bookie_name'] == 'Bwin')
        except StopIteration:
            try:
                both_teams_to_score_odds = next(odd['periods'] for odd in odds_json['data']['prematch'] if odd['name'] == 'Both Teams to Score')
                full_time_odds = next(odd['odds'] for odd in both_teams_to_score_odds if odd['name'] == 'Full Time')
                betclic_full_time_odds = next(odd for odd in full_time_odds if odd['bookie_name'] == '22Bet')
            except:
                odds_url = f"https://oddspedia.com/api/v1/getMatchOdds?wettsteuer=0&geoCode=PT&bookmakerGeoCode=BR&bookmakerGeoState=&matchId={match_id}&oddGroupId=11&inplay=0&language=en"
                odds_json = page.goto(odds_url).json()
                both_teams_to_score_odds = next(odd['periods'] for odd in odds_json['data']['prematch'] if odd['name'] == 'Both Teams to Score')
                full_time_odds = next(odd['odds'] for odd in both_teams_to_score_odds if odd['name'] == 'Full Time')
                betclic_full_time_odds = next(odd for odd in full_time_odds if odd['bookie_name'] == 'Bet365')
    return betclic_full_time_odds['o1'], betclic_full_time_odds['o2']

def get_last_match_df(page, league_id, team_id):
    team_last_matches_url = f"https://oddspedia.com/api/v1/getTeamLastMatches?upcomingMatchesLimit=0&finishedMatchesLimit=50&geoCode=PT&teamId={team_id}&leagueId={league_id}&language=en"
    last_matches = page.goto(team_last_matches_url).json()
    json_last_matches = last_matches['data'][f'{team_id}']['matches']
    last_matches = [LastMatch(**match) for match in json_last_matches if match['outcome'] is not None and match['inplay_status'] != "PEN"]
    return pd.DataFrame(jsonable_encoder(last_matches))

def send_email(df):
    FROM = "doacaosite@gmail.com"
    PASSWORD = "gpeaxofzhbmimfbw"

    msg = email.message.Message()
    msg['From'] = FROM
    msg['To'] = "andreteles56@hotmail.com"
    msg['Subject'] = f"Back Casa para o dia {datetime.date.today()}"
    msg.add_header('Content-Type', 'text')
    msg.set_payload(extractEmailContent(df))

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(FROM, PASSWORD)
    server.sendmail(msg['From'], [msg['To']], msg.as_string().encode('utf-8'))
    server.quit()


def extractEmailContent(df):
    text = "Os jogos que estão dentro do método Back Casa são:\n\n"
    for index, row in df.iterrows():
        text += f"- {row['ht']} vs {row['at']}\n"
    return text


if __name__ == '__main__':
    main()
