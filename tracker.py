from flask import render_template
import pprint as pp
import requests
import json
import os
from flask import Flask, escape, request, jsonify, make_response
from markupsafe import escape
import redis

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

redis_client = redis.Redis()

### Functions ###

def parseDate(dateStr):
    date = ""
    time = ""
    for i in range(0, 10):
        date += dateStr[i]
    for i in range(12, 16):
        time += dateStr[i]
    dt = date + ' ' + time
    return dt

def get_leagueName(leagueID):
    json_obj= requests.get('https://draft.premierleague.com/api/league/' + str(leagueID) + '/details').json()
    return json_obj['league']['name']

def get_currentGw():
    json_obj = requests.get('https://draft.premierleague.com/api/bootstrap-static').json()
    return json_obj['events']['current']

def get_teamInfo(teamID):
    link = 'https://draft.premierleague.com/api/bootstrap-static'
    json_obj= requests.get(link).json()
    teams = json_obj['teams']
    for i in teams:
        if int(teamID) == i['id']:
            team = {
                'id': i['id'],
                'name': i['name'],
                'short_name': i['short_name']
                }
            return team

def findPlayerByID(idNum):
    link = 'https://draft.premierleague.com/api/bootstrap-static'
    json_obj = requests.get(link).json()
    player = {
        'first_name': 'No First Name',
        'last_name': 'No Last Name',
        'web_name': 'No Web Name',
        'gw_points': 0,
        'position': 0,
        'team': 0
        }
    for i in json_obj['elements']:
        if int(i['id']) == int(idNum):
            player = {
                'first_name': i['first_name'],
                'last_name': i['second_name'],
                'web_name': i['web_name'],
                'gw_points': i['event_points'],
                'position': i['element_type'],
                'team': i['team']
                }
    return player

def get_managerList(leagueID):
    url = 'https://draft.premierleague.com/api/league/' + str(leagueID) + '/details'
    r = requests.get(url)
    json_obj = r.json()
    managers = []
    for i in json_obj['league_entries']:
        manager = {
            'id': i['entry_id'],
            'entry_id': i['id'],
            'team_name': i['entry_name'],
            'manager_first_name': i['player_first_name'],
            'manager_last_name': i['player_last_name'],
            'short_name': i['short_name'],
            'waiver_pick': i['waiver_pick']
            }
        managers.append(manager)
    return managers

def get_managerByID(id, leagueID):
    managers = get_managerList(leagueID)
    for i in managers:
        if i['id'] == id:
            return i

def get_managerByEntryID(entry_id, leagueID):
    managers = get_managerList(leagueID)
    for i in managers:
        if i['entry_id'] == entry_id:
            return i

def get_entryID(leagueID, managerID):
    manager_list = get_managerList(leagueID)
    for i in manager_list:
        if i['id'] == managerID:
            return i['entry_id']

def get_managerID(leagueID, managerID):
    manager_list = get_managerList(leagueID)
    for i in manager_list:
        if i['entry_id'] == managerID:
            return i['id']
        
def get_currentOpponent(leagueID, manager_entry_ID):
    curr_gw = get_currentGw()
    json_obj = requests.get('https://draft.premierleague.com/api/league/' + str(leagueID) + '/details').json()
    for i in json_obj['matches']:
        if i['event'] == curr_gw:
            if i['league_entry_1'] == int(manager_entry_ID):
                return i['league_entry_2']
            if i['league_entry_2'] == int(manager_entry_ID):
                return i['league_entry_1']
            else:
                pass
    return "Error"

def get_teamCrest(teamID):
    teams = {
        1: 'Team_Crests/ARS_Crest.png',
        2: 'Team_Crests/AVL_Crest.png',
        3: 'Team_Crests/BHA_Crest.png',
        4: 'Team_Crests/BUR_Crest.png',
        5: 'Team_Crests/CHE_Crest.png',
        6: 'Team_Crests/CP_Crest.png',
        7: 'Team_Crests/EVE_Crest.png',
        8: 'Team_Crests/FUL_Crest.png',
        9: 'Team_Crests/LEI_Crest.png',
        10: 'Team_Crests/LEE_Crest.png',
        11: 'Team_Crests/LIV_Crest.png',
        12: 'Team_Crests/MCI_Crest.png',
        13: 'Team_Crests/MU_Crest.png',
        14: 'Team_Crests/NEW_Crest.png',
        15: 'Team_Crests/SHU_Crest.png',
        16: 'Team_Crests/SOU_Crest.png',
        17: 'Team_Crests/TOT_Crest.png',
        18: 'Team_Crests/WBA_Crest.png',
        19: 'Team_Crests/WHU_Crest.png',
        20: 'Team_Crests/WOL_Crest.png'
        }
    return teams[teamID]

def get_gwPoints(playerID, gw):
    json_obj = requests.get('https://draft.premierleague.com/api/event/' + str(gw) + '/live').json()
    return json_obj['elements'][str(playerID)]['stats']['total_points']

def get_gwInfo(managerID, gw):
    json = requests.get('https://draft.premierleague.com/api/entry/' + str(managerID) + '/event/' + str(gw)).json()
    lineup = []
    for i in json['picks']:
        lineup.append({
            'id': i['element'],
            'name': findPlayerByID(i['element'])['web_name'],
            'team': findPlayerByID(i['element'])['team'],
            'team_crest': get_teamCrest(int(findPlayerByID(i['element'])['team'])),
            'position': i['position'],
            'points': get_gwPoints(i['element'], gw)
            })
    return lineup

def get_playerOpponent(gw, playerID):
    player = findPlayerByID(playerID)
    playerTeam = get_teamInfo(player['team'])
    fixtures = requests.get('https://draft.premierleague.com/api/event/' + str(gw) + '/fixtures').json()
    for i in fixtures:
        if i['team_a'] == int(playerTeam['id']):
            return i['team_h']
        elif i['team_h'] == int(playerTeam['id']):
            return i['team_a']
        
def get_playerStartStatus(gw, team):
    fixtures = requests.get('https://draft.premierleague.com/api/event/' + str(gw) + '/fixtures').json()
    for i in fixtures:
        if i['team_a'] == int(team) or i['team_h'] == int(team):
            if i['started'] == True:
                return True
    return False

def get_playerPoints(playerID, gw):
    json_obj = requests.get('https://draft.premierleague.com/api/element-summary/' + str(playerID)).json()
    fixtures = requests.get('https://draft.premierleague.com/api/event/' + str(gw) + '/live').json()
    player = {}
    stats = []
    for i in fixtures['elements'][str(playerID)]['explain'][0][0]:
        stats.append(i)
    playerInfo = findPlayerByID(playerID)
    for i in json_obj['history']:
        if int(i['event']) == int(gw):
            player = {
                'first_name': playerInfo['first_name'],
                'last_name': playerInfo['last_name'],
                'web_name': playerInfo['web_name'],
                'match_detail': i['detail'],
                'stats': stats
                }
    return player


### Endpoints ###

@app.route('/')
def index():
    return 'hello'

@app.route('/league/name/<leagueID>', methods=['GET'])
def leagueName(leagueID):
    sj = jsonify(get_leagueName(escape(leagueID)))
    sj.headers.add("Access-Control-Allow-Origin", "*")
    return sj

@app.route('/league/<leagueID>/<managerID>/opponent', methods=['GET'])
def get_Opp(leagueID, managerID):
    playerID = get_entryID(int(leagueID), int(managerID))
    manager = get_managerByEntryID(get_currentOpponent(leagueID, playerID), leagueID)
    opponent = jsonify(manager['id'])
    opponent.headers.add("Access-Control-Allow-Origin", "*")
    return opponent

@app.route('/current-week', methods=['GET'])
def currentGw():
    sj = jsonify(get_currentGw())
    sj.headers.add("Access-Control-Allow-Origin", "*")
    return sj

@app.route('/league/standings/<leagueID>', methods=["GET"])
def standings(leagueID):
    standings = []
    json_obj = requests.get('https://draft.premierleague.com/api/league/' + str(leagueID) + '/details').json()
    for i in json_obj['standings']:
        manager = get_managerByEntryID(i['league_entry'], leagueID)
        standings.append({'rank': i['rank'],
                          'manager_id': i['league_entry'],
                          'manager_name': manager['manager_last_name'],
                          'entry_name': manager['team_name'],
                          'matches_won': i['matches_won'],
                          'matches_drawn': i['matches_drawn'],
                          'matches_lost': i['matches_lost'],
                          'total_points': i['total'],
                          'points_for': i['points_for'],
                          'points_against': i['points_against']})
    
    sj = jsonify(standings)
    sj.headers.add("Access-Control-Allow-Origin", "*")

    return sj

@app.route('/league/transactions/<leagueID>/<gameweek>', methods=['GET'])
def get_gwTransactions(leagueID, gameweek):
    waivers = requests.get('https://draft.premierleague.com/api/draft/league/' + str(leagueID) + '/transactions').json()
    current_waivers = []
    for i in waivers['transactions']:
        if int(i['event']) == int(gameweek) and i['result'] == 'a':
            
            
            manager_name = get_managerByID(i['entry'], leagueID)
            player_in = findPlayerByID(i['element_in'])
            player_team = get_teamInfo(player_in['team'])
            player_in_name = player_in['web_name'] + ' (' + player_team['short_name'] + ')'
            
            
            player_out = findPlayerByID(i['element_out'])
            player_team = get_teamInfo(player_out['team'])
            player_out_name = player_out['web_name'] + ' (' + player_team['short_name'] + ')'
            current_waiver = {
                'added_time': parseDate(i['added']),
                'player_in': i['element_in'],
                'player_in_name': player_in_name,
                'player_out': i['element_out'],
                'player_out_name': player_out_name,
                'manager_id': i['entry'],
                'manager_name': manager_name['manager_last_name'],
                'type': None,
                'status': 'accepted'
                }
            if i['kind'] == 'w':
                current_waiver['type'] = 'Waiver'
            elif i['kind'] == 'f':
                current_waiver['type'] = 'Free Agent'
            current_waivers.append(current_waiver)
            
    cw_return = jsonify(current_waivers)
    cw_return.headers.add("Access-Control-Allow-Origin", "*")
                
    return cw_return

@app.route('/league/<managerID>/<gameweek>', methods=['GET'])
def get_Points(managerID, gameweek):
    json = requests.get('https://draft.premierleague.com/api/entry/' + str(managerID) + '/event/' + str(gameweek)).json()
    lineup = []
    for i in json['picks']:
        player_name = findPlayerByID(i['element'])['web_name']
        abbr_name = ''
        if len(player_name) > 13:
            for letter in range(0, 12):
                abbr_name += player_name[letter]
            player_name = abbr_name + '...'
        lineup.append({
            'id': i['element'],
            'name': player_name,
            'team': findPlayerByID(i['element'])['team'],
            'team_crest': get_teamCrest(int(findPlayerByID(i['element'])['team'])),
            'position': i['position'],
            'role': findPlayerByID(i['element'])['position'],
            'points': get_gwPoints(i['element'], gameweek),
            'played': get_playerStartStatus(gameweek, findPlayerByID(i['element'])['team']),
            'opponent': get_teamInfo(get_playerOpponent(int(gameweek), int(i['element'])))['short_name']
            })
    lineup_return = jsonify(lineup)
    lineup_return.headers.add("Access-Control-Allow-Origin", "*")
    
    return lineup_return


@app.route('/league/<leagueID>/managers', methods=['GET'])
def get_Managers(leagueID):
    managers = jsonify(get_managerList(leagueID))
    managers.headers.add("Access-Control-Allow-Origin", "*")
    
    return managers

@app.route('/player/<playerID>/<gw>', methods=['GET'])
def playersPoints(playerID, gw):
    player = get_playerPoints(playerID, gw)
    player_return = jsonify(player)
    player_return.headers.add("Access-Control-Allow-Origin", "*")
    
    return player_return