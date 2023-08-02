import json
import datetime
from time import sleep

import dateutil
from playwright.sync_api import sync_playwright
from Models import Match, LastMatch
from fastapi.encoders import jsonable_encoder
import pandas as pd
import smtplib


def main():
    # file = True
    file = False

    url = 'https://www.oddspedia.com/'
    ua = (
        "Mozilla/5.0 (Windows NT 24.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/69.0.3497.240 Safari/537.36"
    )
    # headers = {'User-Agent': ua,
    #            'Referer': 'https://oddspedia.com/football',
    #            'Accept': 'application/json, text/plain, */*',
    #            'Accept-Language': 'en'}
    #
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=ua)
        if not file:
            page.goto(url)
            page.wait_for_timeout(1000)
            date = datetime.date.today()
            api_url = f"https://oddspedia.com/api/v1/getMatchList?excludeSpecialStatus=0&sortBy=default&perPageDefault=300&startDate={date}T00%3A00%3A00Z&endDate={date}T23%3A59%3A59Z&geoCode=PT&status=all&sport=football&popularLeaguesOnly=0&page=1&perPage=300&language=en"
            data = page.goto(api_url).json()
        else:
            with open("matches.json", "r") as read_file:
                data = json.load(read_file)

        df = get_match_df(data)
        df['ht_form'] = ""
        df['at_form'] = ""
        leagues_id = range(0, 24000)

        filtered_df = df.query('league_id.isin(@leagues_id)')
        print(filtered_df.to_string())

        insert_home_and_away_form(page, filtered_df)
        # filtered_df.to_csv('final_df.csv')
        final_df = filtered_df.query('ht_form.str.count(\'w\') >= 3 & at_form.str.count(\'l\') >= 3')

        send_email(final_df)


def get_match_df(matches):
    json_matchlist = matches['data']['matchList']
    matches = [Match(**match) for match in json_matchlist if match['matchstatus'] == 1]
    return pd.DataFrame(jsonable_encoder(matches))


def get_last_match_df(page, league_id, team_id):
    team_last_matches_url = f"https://oddspedia.com/api/v1/getTeamLastMatches?upcomingMatchesLimit=0&finishedMatchesLimit=24&geoCode=PT&teamId={team_id}&leagueId={league_id}&language=en"
    last_matches = page.goto(team_last_matches_url).json()
    json_last_matches = last_matches['data'][f'{team_id}']['matches']
    last_matches = [LastMatch(**match) for match in json_last_matches if match['outcome'] is not None]
    return pd.DataFrame(jsonable_encoder(last_matches))


def insert_home_and_away_form(page, df):
    for index, row in df.iterrows():
        # sleep(0.05)
        league_id = row['league_id']
        home_team_id = row['ht_id']
        away_team_id = row['at_id']

        raw_home_team_last_matches = get_last_match_df(page, league_id, home_team_id)
        raw_away_team_last_matches = get_last_match_df(page, league_id, away_team_id)

        start_date = (datetime.datetime.now() + dateutil.relativedelta.relativedelta(months=-3)).strftime('%Y-%m-%d')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')

        if not raw_home_team_last_matches.empty and not raw_away_team_last_matches.empty:
            home_team_last_matches = raw_home_team_last_matches.sort_values(by='md', ascending=False).query(
                'ht_id == @home_team_id & md.between(@start_date,@end_date)')
            away_team_last_matches = raw_away_team_last_matches.sort_values(by='md', ascending=False).query(
                'at_id == @away_team_id & md.between(@start_date,@end_date)')

            home_team_form = "".join(home_team_last_matches['outcome'].head().values)
            away_team_form = "".join(away_team_last_matches['outcome'].head().values)

            df.at[index, 'ht_form'] = home_team_form
            df.at[index, 'at_form'] = away_team_form


def send_email(content):
    FROM = "doacaosite@gmail.com"
    PASSWORD = "gpeaxofzhbmimfbw"
    TO = ["andreteles56@hotmail.com"]

    SUBJECT = f"Back Casa para o dia {datetime.date.today()}"

    TEXT = content.to_string().encode('utf-8')

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(FROM, PASSWORD)
    server.sendmail(FROM, TO, TEXT)
    server.quit()


if __name__ == '__main__':
    main()
