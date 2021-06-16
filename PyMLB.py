import time
import requests
import json
from datetime import datetime
from datetime import timedelta
import pytz
import re

eastern = pytz.timezone("US/Eastern")
fmt = "%Y-%m-%d"
today = datetime.today().astimezone().strftime(fmt)
yesterday = (datetime.today().astimezone() - timedelta(days=1)).strftime(fmt)

base_url = "http://statsapi.mlb.com/api/"
alt_base_url = "https://beta-statsapi.mlb.com:443/api/"


def get_json(url):
    ## get_json: str -> json
    ## get_json() function takes "url" and returns the response in json format from the MLB Stats API.
    
    response = requests.get(url)
    if (response.status_code != 200):
        print("status code: %s" % response.status_code)
        time.sleep(1.0)
        get_json(url)
    else:
        content = response.content
        json_content = json.loads(content)
        return(json_content)


def get_attendance(Id,
                teamOrleague = "team",
                date = None,
                startDate = None,
                endDate = None,
                season = None,
                field = "Ytd"):

    url = alt_base_url + "v1/attendance"
    attedance_field = "attendanceAverage" + field 
    
    attendance_dict = {}

    suffix = ""
       
    if not any([date, startDate, endDate, season]):
        date = yesterday
    
    if date is not None:
        suffix += "?date={}".format(date)
        
    if (startDate is not None and endDate is None) or (startDate is None and endDate is not None):
        ValueError("Specify both Start Date and End Date in MM/DD/YYYY format.")

    if startDate is not None and endDate is not None:
        suffix += "?startDate={startDate}&endDate={endDate}".format(startDate = startDate, endDate = endDate)    
        
    if season is not None:
        if type(season) is list:
            suffix += "?season={}".format(",".join(str(s) for s in season))
            
        else:
            suffix += "?season={}".format(season)
            
    
    
    if teamOrleague == "team":
        
        if type(Id) is list:
            ID_str = ",".join(str(i) for i in Id)

        else:
            ID_str = Id

        suffix += "&teamId={teamId}".format(teamId = ID_str)               
                
        attendance_content = get_json(url + suffix)

        records = attendance_content["records"]

        for record in records:
            team = record["team"]["id"]
            attendance = record[attedance_field]

            if date is not None:
                attendance_dict.update({team: {date: attendance}})

            if startDate is not None and endDate is not None:
                attendance_dict.update({team: {"{}".format(startDate + " to " + endDate):attendance}})        
            
            if season is not None:
                if type(season) is list:
                    season_dict = {}
                    for s in season:
                        season_dict.update({s: attendance})
                    attendance_dict.update({team: season_dict})
                
                else:
                    attendance_dict.update({team: {season: attendance}})

    
    if teamOrleague == "league":
        
        if type(Id) is not list:
            Ids = [Id]
            
        else: 
            Ids = Id
        
        for i in Ids:
            suffix += "&leagueId={leagueId}".format(leagueId = i)

            attendance_content = get_json(url + suffix)

            records = attendance_content["records"]

            for record in records:
                league = i
                attendance = record[attedance_field]

                if date is not None:
                    attendance_dict.update({league: {date: attendance}})

                if startDate is not None and endDate is not None:
                    attendance_dict.update({league: {"{}".format(startDate + " to " + endDate):attendance}})    
                    
                if season is not None:
                    if type(season) is list:
                        season_dict = {}
                        for s in season:
                            season_dict.update({s: attendance})
                        attendance_dict.update({league: season_dict})
                    else:
                        attendance_dict.update({league: {season: attendance}})
                        
                        
    return(attendance_dict)


def get_division():
    
    division_url = "http://statsapi.mlb.com/api/v1/divisions?sportId=1"
    division_content = get_json(division_url)
    divisions = division_content["divisions"]
    
    division_filter = ["id", "name", "nameShort", "abbreviation"]
    
    division_list = [{k:v for k,v in d.items() if k in division_filter} for d in divisions]
    
    return(division_list)


def lookup_division(divisionId, 
					field = "nameShort"):
    
    division_list = get_division()
    division_wanted = [d[field] for d in division_list if divisionId in d.values()][0]
    
    return(division_wanted)
    

def get_linescore(gamePk):
    
    team_url = base_url + "v1/schedule?gamePk={gamePk}".format(gamePk = gamePk)
    team_content = get_json(team_url)
    
    teams = team_content["dates"][0]["games"][0]["teams"]
    
    team_dict = {"teams": {k: {x: y for x,y in v["team"].items() if x == "id" or x == "name"} for k, v in teams.items()}}
    
    
    ls_url = base_url + "/v1/game/{gamePk}/linescore".format(gamePk = gamePk)
    linescore_content = get_json(ls_url)
    
    linescore_dict = {}
    
    innings = linescore_content["innings"]
    
    for inning in innings:
        inn_count = inning["ordinalNum"]
        home = {x: y for x, y in inning["home"].items() if x != "leftOnBase"} 
        away = {x: y for x, y in inning["away"].items() if x != "leftOnBase"} 
        
        linescore_dict.update({inn_count: {"home": home, "away": away}})
    
    linescore_dict.update(team_dict)
    
    return(linescore_dict)


def get_pitchfx(gamePk):
    
    bs_url = base_url + "/v1/game/{gamePk}/boxscore".format(gamePk = gamePk)
    bs_content = get_json(bs_url)
    bs_info = bs_content['info']

    umpires = [l for l in bs_info if l['label'] == "Umpires"][0]['value']
    home_umpire = re.findall("HP: [\w \.]+ 1B:", umpires)[0].lstrip("HP: ").rstrip(". 1B:")

    pbp_url = base_url + "/v1/game/{gamePk}/playByPlay".format(gamePk = gamePk)
    pbp_content = get_json(pbp_url)
    
    allPlays = pbp_content['allPlays']
       
    atBat_dict = {"home_umpire": home_umpire}
    
    for play in allPlays:
                
        about = play['about']
        
        atBat_count = about['atBatIndex']        
        inning = about['inning']
        home = "home" if about['isTopInning'] else "away"
        
        matchup = play['matchup']
        pitcher = matchup['pitcher']
        batter = matchup['batter']
        pitchHand = matchup['pitchHand']['code']
        batSide = matchup['batSide']['code']      
        
        """
        matchup_dict = {'pitcher': pitcher,
                       'batter': batter,
                       'pitchHand': pitchHand,
                       'batSide': batSide}
        """
        atBat_dict.update({atBat_count: {"inning": inning, 
                                         "home": home, 
                                         'pitcher': pitcher,
                                         'batter': batter,
                                         'pitchHand': pitchHand,
                                         'batSide': batSide}})
        
        events = play['playEvents']     
        pitched_events = (event for event in events if event['isPitch'])
        
        pitch_list = []
        
        for event in pitched_events:
            
            if not event['isPitch']:
                continue
            

            if event['details']['isInPlay']:
                continue

            if event['details']['description'] == "Foul":
                continue

            """
            strike = event['details']['isStrike']
            
            pitch_index = event['index']
            """
            try:

                strike = "strike" if not event['details']['isBall'] else "ball"

                pitch_data = event['pitchData']
                
                sz_top = pitch_data['strikeZoneTop']
                sz_bottom = pitch_data['strikeZoneBottom']
                x = pitch_data['coordinates']['pX']
                z = pitch_data['coordinates']['pZ']
                
                #pitch_dict = {pitch_index: {'call': strike, 'sz_top': sz_top, 'sz_bottom': sz_bottom, 'x': x, 'z': z}}
                pitch_list.append({'call': strike, 'sz_top': sz_top, 'sz_bottom': sz_bottom, 'x': x, 'z': z})
            
            except:
                pass
        atBat_dict[atBat_count]['pitchData'] = pitch_list
            
    return(atBat_dict)


def lookup_player(name):
    """
    returns personId for given player name
    """
    sports_url = base_url + "/v1/sports/1/players"
    sports_content = get_json(sports_url)
    
    players = sports_content["people"]
    
    matching_player = [player for player in players if str(name).lower() in str(player.values()).lower()]
    
    if len(matching_player) == 1:
        return(matching_player[0]["id"])
    
    return(matching_player)


def lookup_player_info(playerId):
        
    person_url = base_url + "v1/people/{}/".format(playerId)
    person_content = get_json(person_url)
    profile = person_content["people"][0]
    
    return(profile)


def player_game_stat(personId, 
					gamePk):
    
    game_stat_url = base_url + "v1/people/{playerId}/stats/game/{gamePk}".format(playerId = personId, gamePk = gamePk)
    game_stat_content = get_json(game_stat_url)
    game_stat = game_stat_content["stats"]
    
    stats = [s for s in game_stat if s["splits"]]
    
    stat_dict = {}
    
    try:    
        for s in stats:        
            t = s["group"]["displayName"]
            splits = s["splits"]
            stat = splits[0]["stat"]
            stat_dict.update({t:stat})
        return(stat_dict)

    except:
        print("The player did not play in the stated game.")
    

def get_schedule(date = None,
                 startDate = None,
                 endDate = None,
                 teamId = None,
                 season = None,
                 sportId = 1):
    
    schedule_base_url = base_url + "/v1/schedule?sportId=1"
    
    """
    if not any([date, startDate, endDate]):
        date = today
    """
    suffix = ""
    
    if date is not None:
        suffix += "&date={}".format(date)
        
    if (startDate is not None and endDate is None) or (startDate is None and endDate is not None):
        ValueError("Specify both Start Date and End Date in MM/DD/YYYY format.")
        
    if startDate is not None and endDate is not None:
        suffix += "&startDate={startDate}&endDate={endDate}".format(startDate = startDate, endDate = endDate)
        
    if teamId is not None:
        suffix += "&teamId={}".format(teamId)
        
    schedule_url = schedule_base_url + suffix
    print(schedule_url)
    schedule_content = get_json(schedule_url)
    
    schedule_dict = {}
    
    dates = schedule_content["dates"]
    
    for d in dates:
        day = d["date"]
        games = d["games"]
        
        games_list = []
        
        for game in games:
            gameID = game["gamePk"]
            
            teams = game["teams"]
            away = teams["away"]
            away_name = away["team"]["name"]
            away_Id = away["team"]["id"]
            
            home = teams["home"]
            home_name = home["team"]["name"]
            home_Id = home["team"]["id"]
            
            games_list.append({"gamePk": gameID, 
                               "home": {"ID": home_Id, "name": home_name},
                               "away":{"ID": away_Id, "name": away_name}})
            
        schedule_dict.update({day:games_list})
        
    return(schedule_dict)


def get_season(season):
    """
    returns season start and end dates
    """
    season_url = base_url + "v1/seasons?season={}&sportId=1".format(season)
    season_content = get_json(season_url)
    
    return(season_content["seasons"][0])


def get_standings(leagueID = None, 
					season = 2021):
    """
    leagueId is the mandatory parameter in this API query.
    """
    suffix = ""
    base_standings_url = base_url + "v1/standings"
    
    if leagueID is None:
        suffix += "?leagueId=103,104"
        
    else:
        suffix += "?leaugeId={}".format(leagueId)
    
    suffix += "&season={}".format(season)
    
    standings_url = base_standings_url + suffix
    records = get_json(standings_url)["records"]
    
    division_dict = {}
    
    for record in records:
        
        division = lookup_division(record["division"]["id"])
        
        team_records = record["teamRecords"]
        
        tr_dict = {}
        
        for tr in team_records:

            team_name = tr["team"]["name"]
            rank = tr["divisionRank"]
            gamesPlayed = tr["gamesPlayed"]
            gamesBack = tr["gamesBack"]
            wins = tr["leagueRecord"]["wins"]
            losses = tr["leagueRecord"]["losses"]
            pct = tr["leagueRecord"]["pct"]

            tr_dict.update({team_name:{"rank":rank, "Played": gamesPlayed, "W": wins, "L": losses, "%": pct, "gamesBack": gamesBack}})
            
        division_dict.update({division:tr_dict})
        
    return(division_dict)


def lookup_team(name):
    """
    returns personId for given player name
    """
    team_url = base_url + "/v1/teams?sportId=1"
    team_content = get_json(team_url)
    teams = team_content["teams"]
    
    matching_team = [team for team in teams if str(name).lower() in str(team.values()).lower()]
    
    if len(matching_team) == 1:
        return(matching_team[0]["id"])
    
    return(matching_team)


def lookup_roster(teamId, 
				season = 2021, 
                rosterType = "40man"):
    """
    rosterType can be either one of "40man", "fullSeason", "full", or "active"
    """
    
    roster_url = base_url + "v1/teams/{teamId}/roster/{rosterType}?season={season}".format(teamId = teamId,
                                                                                          rosterType = rosterType,
                                                                                          season = season)
    
    roster = get_json(roster_url)["roster"]
    
    return(roster)