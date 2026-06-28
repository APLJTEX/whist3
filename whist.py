from playcard import *
import random
import json

# ====== 调试工具函数 ======
def debug_log(message, state=None):
    """用于调试，可以在日志中查看状态"""
    print(f"[DEBUG] {message}")
    if state:
        # 只打印关键字段，避免太长
        debug_state = {
            'stop_type': state.get('stop_type'),
            'current_trick_len': len(state.get('current_trick', [])),
            'trick_history_len': len(state.get('trick_history', [])),
            'hands_south_len': len(state['hands']['south']) if state.get('hands') else 0,
            'message': state.get('message', '')
        }
        print(f"  State: {json.dumps(debug_state, indent=2)}")

def find_valid_cards(hand, lead_suit):
    if lead_suit is None:
        return hand[:]
    return [card for card in hand if get_suit(card) == lead_suit]

def sort_hand(hand):
    suit_order = {'C': 0, 'D': 1, 'H': 2, 'S': 3}
    return sorted(hand, key=lambda card: (suit_order[get_suit(card)], -get_rank_ace_high(card)))

def get_card_display_name(card):
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

def determine_trick_winner(trick, trump_suit):
    """简化版：确保输入是[(player, card), ...]格式"""
    if not trick:
        return 'north'
    
    # 确保格式统一
    if isinstance(trick[0], dict):
        trick = [(item['player'], item['card']) for item in trick]
    
    lead_suit = get_suit(trick[0][1])
    winning_card = find_highest_card([c for _, c in trick], trump_suit, lead_suit)
    for player, card in trick:
        if card == winning_card:
            return player
    return trick[0][0]

def ai_play_card(player, hand, current_trick, trump_suit, game_state):
    # 处理current_trick格式
    lead_suit = None
    if current_trick:
        if isinstance(current_trick[0], dict):
            lead_suit = get_suit(current_trick[0]['card'])
        else:
            lead_suit = get_suit(current_trick[0][1])

    valid_cards = find_valid_cards(hand, lead_suit)

    if lead_suit is not None and valid_cards != hand:
        same_suit_cards = []
        for item in current_trick:
            card = item['card'] if isinstance(item, dict) else item[1]
            if get_suit(card) == lead_suit:
                same_suit_cards.append(card)
        
        highest_in_suit = max(same_suit_cards, key=get_rank_ace_high) if same_suit_cards else None
        
        if highest_in_suit is not None:
            winning_cards = [c for c in valid_cards if get_rank_ace_high(c) > get_rank_ace_high(highest_in_suit)]
            if winning_cards:
                return min(winning_cards, key=get_rank_ace_high)
        return min(valid_cards, key=get_rank_ace_high)

    # 清短套策略
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
        'current_trick': [],  # 始终保持为列表格式
        'leader': 'north',
        'players': players,
        'trump_suit_name': trump_info['svg'],
        'message': game_message,
        'message_class': "info-message",
        'stop_type': 'new_trick',
        'trick_number': 1,
        'trick_history': []
    }

    session['game_state'] = game_state
    debug_log("New game initialized", game_state)
    return game_state


def game_update(session, action):
    """终极修复版：使用明确的状态转换"""
    game_state = session.get('game_state')
    if not game_state:
        debug_log("No game state found, creating new game")
        return new_game(session)

    hands = game_state['hands']
    trump_suit = game_state['trump_suit']
    current_trick = game_state.get('current_trick', [])
    trick_history = game_state.get('trick_history', [])
    
    debug_log(f"game_update called with action: {action}", game_state)

    # ====== 状态机：明确的四个阶段 ======
    # 1. NEW_TRICK: North出牌 → West出牌 → 进入FOLLOW_CARD
    # 2. FOLLOW_CARD: South出牌 → East出牌 → 判定赢家 → 进入NEXT_TRICK或GAME_OVER
    # 3. NEXT_TRICK: 准备下一墩
    # 4. GAME_OVER: 游戏结束

    # --- 阶段1: 新墩开始 ---
    if game_state.get('stop_type') == 'new_trick':
        debug_log("Entering NEW_TRICK phase")
        
        # 初始化当前墩
        game_state['current_trick'] = []
        game_state['trick_history'] = []
        game_state['message'] = "New trick started. North leads."
        
        # North出牌
        north_card = ai_play_card('north', hands['north'], [], trump_suit, game_state)
        hands['north'].remove(north_card)
        hands['north'] = sort_hand(hands['north'])
        
        game_state['current_trick'] = [('north', north_card)]
        north_display = get_card_display_name(north_card)
        game_state['trick_history'] = [{'player': 'north', 'card': north_card, 'display_position': 0, 'display_name': north_display}]
        game_state['message'] = f"North played {north_display}."
        
        # West出牌
        west_card = ai_play_card('west', hands['west'], game_state['current_trick'], trump_suit, game_state)
        hands['west'].remove(west_card)
        hands['west'] = sort_hand(hands['west'])
        
        game_state['current_trick'].append(('west', west_card))
        west_display = get_card_display_name(west_card)
        game_state['trick_history'].append({'player': 'west', 'card': west_card, 'display_position': 1, 'display_name': west_display})
        game_state['message'] = f"West played {west_display}."
        
        # 设置为等待South出牌
        game_state['stop_type'] = 'follow_card'
        
        # 更新手牌
        game_state['hands'] = {
            'north': hands['north'],
            'east': hands['east'],
            'south': hands['south'],
            'west': hands['west']
        }
        
        session['game_state'] = game_state
        debug_log("NEW_TRICK phase completed, now in FOLLOW_CARD", game_state)
        return game_state

    # --- 阶段2: 人类玩家出牌（South）---
    if action and isinstance(action, str) and action.startswith('play_'):
        debug_log("Processing South's play action")
        
        played_card = action.replace('play_', '')
        
        # 验证合法性
        if not game_state['current_trick']:
            debug_log("Error: current_trick is empty!")
            game_state['message'] = "Game error: no current trick."
            game_state['message_class'] = "error-message"
            session['game_state'] = game_state
            return game_state
            
        lead_suit = get_suit(game_state['current_trick'][0][1])
        valid_cards = find_valid_cards(hands['south'], lead_suit)
        
        if played_card not in valid_cards:
            debug_log(f"Invalid move: {played_card} not in valid cards {valid_cards}")
            game_state['message'] = "Invalid move! You must follow suit."
            game_state['message_class'] = "error-message"
            session['game_state'] = game_state
            return game_state

        # South出牌
        hands['south'].remove(played_card)
        hands['south'] = sort_hand(hands['south'])
        game_state['current_trick'].append(('south', played_card))
        
        south_display = get_card_display_name(played_card)
        game_state['trick_history'].append({
            'player': 'south',
            'card': played_card,
            'display_position': 2,
            'display_name': south_display
        })
        game_state['message'] = f"You played {south_display}."
        
        # ====== 关键：立即执行East出牌，不等待用户 ======
        debug_log("Executing East's automatic play")
        
        east_card = ai_play_card('east', hands['east'], game_state['current_trick'], trump_suit, game_state)
        hands['east'].remove(east_card)
        hands['east'] = sort_hand(hands['east'])
        game_state['current_trick'].append(('east', east_card))
        
        east_display = get_card_display_name(east_card)
        game_state['trick_history'].append({
            'player': 'east',
            'card': east_card,
            'display_position': 3,
            'display_name': east_display
        })
        game_state['message'] = f"East played {east_display}."
        
        # 检查是否完成一墩（必须有4张牌）
        if len(game_state['current_trick']) == 4:
            debug_log("Trick complete, determining winner")
            
            # 判定赢家
            winner = determine_trick_winner(game_state['current_trick'], trump_suit)
            
            # 更新分数
            if winner in ['south', 'north']:
                game_state['scores']['south_north'] += 1
            else:
                game_state['scores']['east_west'] += 1

            # 保存此墩
            trick_dict = {}
            for player, card in game_state['current_trick']:
                trick_dict[player] = card
            game_state['tricks'].append(trick_dict)
            
            # 重置当前墩
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
                game_state['stop_type'] = 'new_trick'  # 下一墩开始

        # 更新手牌
        game_state['hands'] = {
            'north': hands['north'],
            'east': hands['east'],
            'south': hands['south'],
            'west': hands['west']
        }
        
        session['game_state'] = game_state
        debug_log("South play processed successfully", game_state)
        return game_state

    # --- 默认情况：返回当前状态 ---
    debug_log("Returning current state without changes")
    return game_state
