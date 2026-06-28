from playcard import *
import random


def find_valid_cards(hand, lead_suit):
    """找出手中所有符合'跟花色'规则的牌。"""
    if lead_suit is None:  # 首攻，可以出任意牌
        return hand[:]
    return [card for card in hand if get_suit(card) == lead_suit]


def sort_hand(hand):
    """对一手牌进行排序：先按花色(♣, ♢, ♡, ♠)，再按点数(A, K, Q, J, 10...)"""
    suit_order = {'C': 0, 'D': 1, 'H': 2, 'S': 3}
    return sorted(hand, key=lambda card: (suit_order[get_suit(card)], -get_rank_ace_high(card)))


def get_card_display_name(card):
    """将内部牌表示转换为人类可读的名称"""
    rank = str(get_rank_ace_high(card))
    suit = get_suit(card)
    
    rank_names = {'14': 'Ace', '13': 'King', '12': 'Queen', '11': 'Jack'}
    suit_names = {'C': 'Clubs', 'D': 'Diamonds', 'H': 'Hearts', 'S': 'Spades'}
    
    rank_name = rank_names.get(rank, rank)
    suit_name = suit_names.get(suit, suit)
    return f"{rank_name} of {suit_name}"


def find_highest_card(cards, trump_suit=None, lead_suit=None):
    if not cards:
        return None
    if trump_suit is not None:
        trumps = [c for c in cards if get_suit(c) == trump_suit]
        if trumps:
            return max(trumps, key=get_rank_ace_high)
    if lead_suit is not None:
        same_suit = [c for c in cards if get_suit(c) == lead_suit]
        if same_suit:
            return max(same_suit, key=get_rank_ace_high)
    return max(cards, key=get_rank_ace_high)


def determine_trick_winner(trick, trump_suit, leader_index=0):
    """修正版：确保trick格式正确"""
    if not trick:
        return 'north'
    
    # 确保trick是[(player, card), ...]格式
    if isinstance(trick[0], dict):
        # 如果是字典格式，转换为元组格式
        trick_tuples = [(item['player'], item['card']) for item in trick]
    else:
        trick_tuples = trick
    
    lead_suit = get_suit(trick_tuples[leader_index][1])
    winning_card = find_highest_card([c for _, c in trick_tuples], trump_suit, lead_suit)
    for player, card in trick_tuples:
        if card == winning_card:
            return player
    return trick_tuples[0][0]


def ai_play_card(player, hand, current_trick, trump_suit, game_state):
    lead_suit = None
    if current_trick:
        # 修正：处理current_trick可能是字典列表的情况
        if isinstance(current_trick[0], dict):
            lead_suit = get_suit(current_trick[0]['card'])
        else:
            lead_suit = get_suit(current_trick[0][1])

    valid_cards = find_valid_cards(hand, lead_suit)

    if lead_suit is not None and valid_cards != hand:
        same_suit_cards = []
        for item in current_trick:
            if isinstance(item, dict):
                if get_suit(item['card']) == lead_suit:
                    same_suit_cards.append(item['card'])
            else:
                if get_suit(item[1]) == lead_suit:
                    same_suit_cards.append(item[1])
        
        highest_in_suit = max(same_suit_cards, key=get_rank_ace_high) if same_suit_cards else None
        
        if highest_in_suit is not None:
            winning_cards = [c for c in valid_cards if get_rank_ace_high(c) > get_rank_ace_high(highest_in_suit)]
            if winning_cards:
                return min(winning_cards, key=get_rank_ace_high)
        return min(valid_cards, key=get_rank_ace_high)

    suit_counts = {}
    for card in hand:
        s = get_suit(card)
        suit_counts[s] = suit_counts.get(s, 0) + 1

    non_trump_suits = {s: count for s, count in suit_counts.items() if s != trump_suit}
    if non_trump_suits:
        shortest_suit = min(non_trump_suits, key=non_trump_suits.get)
        shortest_suit_cards = [c for c in hand if get_suit(c) == shortest_suit]
        if shortest_suit_cards:
            return min(shortest_suit_cards, key=get_rank_ace_high)

    non_trump_cards = [c for c in hand if get_suit(c) != trump_suit]
    if non_trump_cards:
        return min(non_trump_cards, key=get_rank_ace_high)

    trump_cards = [c for c in hand if get_suit(c) == trump_suit]
    if trump_cards:
        return min(trump_cards, key=get_rank_ace_high)

    return valid_cards[0]


def new_game(session):
    deck = make_deck()
    random.shuffle(deck)

    hands = {
        'north': deck[0:13],
        'east': deck[13:26],
        'south': deck[26:39],
        'west': deck[39:52]
    }

    trump_card = deck[51]
    trump_suit = get_suit(trump_card)
    
    trump_svg_map = {
        'S': {'svg': 'spade', 'name': 'Spade', 'symbol': '♠'},
        'H': {'svg': 'heart', 'name': 'Heart', 'symbol': '♥'},
        'D': {'svg': 'diamond', 'name': 'Diamond', 'symbol': '♦'},
        'C': {'svg': 'club', 'name': 'Club', 'symbol': '♣'}
    }
    trump_info = trump_svg_map.get(trump_suit, trump_svg_map['S'])
    
    players = {
        'north': 'North (AI)',
        'east': 'East (AI)',
        'south': 'South (You)',
        'west': 'West (AI)'
    }
    
    suit_names = {'S': 'Spades', 'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs'}
    game_message = f"Trump suit is {suit_names.get(trump_suit, trump_suit)}! Ready for a new trick."

    sorted_hands = {
        'north': sort_hand(hands['north']),
        'east': sort_hand(hands['east']),
        'south': sort_hand(hands['south']),
        'west': sort_hand(hands['west'])
    }

    game_state = {
        'hands': sorted_hands,
        'trump_suit': trump_suit,
        'trump_card': trump_card,
        'scores': {'south_north': 0, 'east_west': 0},
        'tricks': [],
        'current_trick': [],  # 使用列表存储当前墩
        'leader': 'north',
        'players': players,
        'trump_suit_name': trump_info['svg'],
        'message': game_message,
        'message_class': "info-message",
        'stop_type': 'new_trick',
        'trick_number': 1,
        'trick_history': []  # 存储完整的出牌历史
    }

    session['game_state'] = game_state
    return game_state


def game_update(session, action):
    game_state = session.get('game_state')
    if not game_state:
        return new_game(session)

    hands = game_state['hands']
    trump_suit = game_state['trump_suit']
    current_trick = game_state.get('current_trick', [])
    trick_history = game_state.get('trick_history', [])
    
    # ====== 关键修复：统一数据结构 ======
    # 确保current_trick是[(player, card), ...]格式
    if current_trick and isinstance(current_trick[0], dict):
        current_trick = [(item['player'], item['card']) for item in current_trick]
        game_state['current_trick'] = current_trick

    # --- 处理新墩开始 ---
    if action == 'new_trick':
        game_state['current_trick'] = []
        game_state['leader'] = 'north'
        game_state['message'] = "New trick started. North leads."
        game_state['trick_history'] = []
        
        # North出牌
        north_card = ai_play_card('north', hands['north'], [], trump_suit, game_state)
        hands['north'].remove(north_card)
        hands['north'] = sort_hand(hands['north'])
        
        # 更新current_trick为元组格式
        current_trick = [('north', north_card)]
        game_state['current_trick'] = current_trick
        
        # 记录North出牌到trick_history
        north_display = get_card_display_name(north_card)
        game_state['trick_history'] = [{
            'player': 'north',
            'card': north_card,
            'display_position': 0,
            'display_name': north_display
        }]
        
        game_state['message'] = f"North played {north_display}."
        
        # West出牌
        west_card = ai_play_card('west', hands['west'], current_trick, trump_suit, game_state)
        hands['west'].remove(west_card)
        hands['west'] = sort_hand(hands['west'])
        
        current_trick.append(('west', west_card))
        game_state['current_trick'] = current_trick
        
        # 记录West出牌
        west_display = get_card_display_name(west_card)
        game_state['trick_history'].append({
            'player': 'west',
            'card': west_card,
            'display_position': 1,
            'display_name': west_display
        })
        
        game_state['message'] = f"West played {west_display}."
        
        # 现在轮到South出牌
        game_state['stop_type'] = 'follow_card'
        
        # 更新手牌
        game_state['hands'] = {
            'north': hands['north'],
            'east': hands['east'],
            'south': hands['south'],
            'west': hands['west']
        }
        
        session['game_state'] = game_state
        return game_state

    # --- 人类玩家出牌 ---
    if action and isinstance(action, str) and action.startswith('play_'):
        played_card = action.replace('play_', '')
        
        # 验证出牌合法性
        lead_suit = get_suit(game_state['current_trick'][0][1]) if game_state['current_trick'] else None
        valid_cards = find_valid_cards(hands['south'], lead_suit)
        if played_card not in valid_cards:
            game_state['message'] = "Invalid move! You must follow suit."
            game_state['message_class'] = "error-message"
            session['game_state'] = game_state
            return game_state

        # South出牌
        hands['south'].remove(played_card)
        hands['south'] = sort_hand(hands['south'])
        current_trick.append(('south', played_card))
        game_state['current_trick'] = current_trick
        
        # 记录South出牌
        south_display = get_card_display_name(played_card)
        game_state['trick_history'].append({
            'player': 'south',
            'card': played_card,
            'display_position': 2,
            'display_name': south_display
        })
        
        game_state['message'] = f"You played {south_display}."

        # ====== East自动出牌 ======
        east_card = ai_play_card('east', hands['east'], current_trick, trump_suit, game_state)
        hands['east'].remove(east_card)
        hands['east'] = sort_hand(hands['east'])
        current_trick.append(('east', east_card))
        
        # 记录East出牌
        east_display = get_card_display_name(east_card)
        game_state['trick_history'].append({
            'player': 'east',
            'card': east_card,
            'display_position': 3,
            'display_name': east_display
        })
        
        game_state['message'] = f"East played {east_display}."

        # 检查是否完成一墩（4张牌）
        if len(current_trick) == 4:
            # 判定赢家
            winner = determine_trick_winner(current_trick, trump_suit)
            
            # 更新分数
            if winner in ['south', 'north']:
                game_state['scores']['south_north'] += 1
            else:
                game_state['scores']['east_west'] += 1

            # 保存此墩
            trick_dict = {}
            for player, card in current_trick:
                trick_dict[player] = card
            game_state['tricks'].append(trick_dict)
            game_state['current_trick'] = []
            game_state['leader'] = winner
            game_state['trick_number'] = len(game_state['tricks']) + 1

            # 检查游戏结束
            if len(game_state['tricks']) == 13:
                sn_score = game_state['scores']['south_north']
                ew_score = game_state['scores']['east_west']
                if sn_score >= 7:
                    game_state['message'] = f"South-North wins the game! Final score: {sn_score}-{ew_score}"
                else:
                    game_state['message'] = f"East-West wins the game! Final score: {ew_score}-{sn_score}"
                game_state['stop_type'] = 'game_over'
            else:
                game_state['message'] = f"{winner.capitalize()} wins the trick! They will lead the next one."
                game_state['stop_type'] = 'new_trick'

        # 更新手牌
        game_state['hands'] = {
            'north': hands['north'],
            'east': hands['east'],
            'south': hands['south'],
            'west': hands['west']
        }
        
        session['game_state'] = game_state
        return game_state

    # 默认返回
    return game_state
