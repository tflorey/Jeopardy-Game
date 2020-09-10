import PySimpleGUI as sg
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import re, time
import pandas as pd

#for checking raw data/errors
'''pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', -1)'''

# set options for selenium browser
options = Options()
options.headless = True
options.add_argument("--window-size=1920,1200")
driver = webdriver.Chrome(options=options)

# determines all fonts in the game (apart from jeopardy board which is pre set)
gameFont = ('Verdana',22)

# implement our own style for windows to match jeopardy color scheme
sg.LOOK_AND_FEEL_TABLE['Jeopardy'] = {'BACKGROUND': '#151680',
                                        'TEXT': '#ffffff',
                                        'INPUT': '#ffffff',
                                        'TEXT_INPUT': '#000',
                                        'SCROLL': '#c7e78b',
                                        'BUTTON': ('#ffd300', '#1c44ac'),
                                        'PROGRESS': ('#01826B', '#D0D0D0'),
                                        'BORDER': 1, 'SLIDER_DEPTH': 0, 'PROGRESS_DEPTH': 0,
                                        }
# set theme to what we created
sg.theme('Jeopardy')

# checks that user input is an integer >= 0 for Daily Double wagers
def inputValidation(value):
    try:
        if int(value)>=0:
            return True
        return False
    except ValueError:
        return False

# creates window with instructions on game mechanics/how to play
def instructions():
    # message
    instruc = ('To play Jeopardy, we will offer a clue, and you will enter the '
    'appropriate question pertaining to the response. To do so, you will click '
    'a category for an amount of money. The clue will pop up, and there will be '
    'a 10 second countdown to read the clue. If you would like to answer, hit '
    'the space bar. Then you will have 10 seconds to type your response. If your '
    'response is correct, your score will increase by the amount of the clue. '
    'If you choose to buzz in and answer incorrectly then your score will decrease '
    'by the amount of the clue. If you do not buzz in, your score will not be '
    'affected.')
    layout = [
        [sg.Text(instruc,size=(50,10),font=gameFont,justification='center')],
        [sg.Text(size=(22,1),font=gameFont),sg.Button('Close',font=gameFont,size=(6,1)),
        sg.Text(size=(22,1),font=gameFont)] #empty text provides buffer to center button
    ]
    instructionWindow = sg.Window('Instructions',layout)
    while True:
        event, values = instructionWindow.read()
        if event == sg.WIN_CLOSED or event == 'Close':
            instructionWindow.close()
            break

# get user input for the season to pick
def getSeason(): # use web scraping to return number of games in the season requested
    url = 'http://j-archive.com/listseasons.php'
    driver.get(url)

    # find element that determines the number of seasons
    seasons = driver.find_element_by_xpath("//div[@id='content']/table/tbody/tr[2]/td/a")

    # remove string 'Season" and give only number
    numSeasons = seasons.text.split(' ',1)[1]
    numSeasons = int(numSeasons)

    # welcome message to display
    welcome = ("Welcome to Jeopardy! We will prompt you for a season and a game from "
    "that season. Please be patient through this process while we fetch that "
    "data. Thanks and have fun playing!")
    message = (f"There have been {numSeasons} seasons of Jeopardy! Pick a season:")

    # declare window layout with message, input, and submit
    layout = [
        [sg.Text(welcome, size=(55,3),justification='center',font=gameFont)],
        [sg.Text(message,size=(30,2), font=gameFont,justification='center'),\
            sg.In(size=(10,1),font=gameFont,focus=True),\
            sg.Submit(size=(10,1),font=gameFont)
        ]
    ]
    # create window with declared layout
    seasonWindow = sg.Window('Jeopardy!',layout)
    gotSeason = False # determines if user input is valid
    while True:
        event, values = seasonWindow.read()
        if event == sg.WIN_CLOSED:
            break
        elif event == 'Submit':
            if inputValidation(values[0]):
                season = int(values[0])
                if(season <= numSeasons and season>0):
                    seasonWindow.close()
                    gotSeason = True
                    season = values[0]
                    break
    if gotSeason:
        getGame(season)

# get user input for the game from the season
def getGame(season):
    # now web scrape to return that game the user requested and begin playing
    url = 'http://www.j-archive.com/showseason.php?season=' + season
    driver.get(url)
    games_elems = driver.find_elements_by_xpath('//div[@id="content"]/table/tbody/tr/td[@align="left"]/a')
    numGames = len(games_elems)
    message = f'There are {numGames} games in season {season}. Pick one to play:'
    gotGame = False # determines if user input is valid
    layout = [
        [sg.Text(message,size=(18,3),font=gameFont,justification='center')],
        [sg.In(focus=True,size=(8,1),font=gameFont),sg.Submit(font=gameFont,size=(8,1))]
    ]
    gameWindow = sg.Window('Pick a game!',layout,use_default_focus=False)
    gameWindow.Finalize() # 2nd window loses focus so this is a fix
    gameWindow.TKroot.focus_force() # forces focus on window instead of shell
    while True:
        event, values = gameWindow.read()
        if event == sg.WIN_CLOSED:
            break
        elif event == 'Submit':
            if inputValidation(values[0]):
                numGame = int(values[0])
                if numGame<=numGames and numGame>0:
                    game = games_elems[numGames-numGame]
                    gotGame = True
                    gameWindow.close()
                    break
    if gotGame:
        startGame(game,numGame,season)

# window after game loads allowing user to hit 'play' or 'instructions'
def startGame(game,numGame,season): # we will have a 'your game is ready' screen here
    # this is where the real web scraping occurs so have loading window popup
    game.click()
    # grab all categories from the page
    category_elems = driver.find_elements_by_xpath('//table[@class="round"]/tbody/tr/td[@class="category"]/table/tbody/tr/td[@class="category_name"]')
    # grab all clue boxes (even those without data)
    clue_entity = driver.find_elements_by_xpath('//table[@class="round"]/tbody/tr/td[@class="clue"]')
    # now grab only the clues that have data
    clue_elems = driver.find_elements_by_xpath('//table[@class="round"]/tbody/tr/td[@class="clue"]/table/tbody/tr/td[@class="clue_text"]')
    # grab all answers from the page (these also are only those with answers)
    answers_elem = driver.find_elements_by_class_name('clue_header')
    # create variables for holding all of these values
    categories = []
    answers = []
    amounts = []
    clues = []

    # loop through categories and grab text
    for item in category_elems:
        categories.append(item.text)
    # split into first and second half and times 5 for all 5 questions in the category
    first_half = categories[0:6]*5
    second_half = categories[6:12]*5
    # combine for full list of categories
    categories = first_half + second_half

    index = 0 # used to track when there is empty data in the archive
    index_entity = 0 # 60 clue "entities" but some don't have data
    # loop through each clue and add '???' if no data or text if data
    while index_entity<60:
        if clue_entity[index_entity].text:
            clues.append(clue_elems[index].text)
            item = answers_elem[index]
            text = re.search('([a-zA-Z0-9]+)',item.text)
            if text:
                amounts.append(text.group(1))
            try:
                try: # first try clicking to trigger the correct response
                    item.click()
                    answer_elem = driver.find_element_by_class_name('correct_response')
                    answers.append(answer_elem.text)
                    item.click()
                except: # if this does not work then hover to trigger the correct response
                    hover = ActionChains(driver).move_to_element_with_offset(item,0,0)
                    hover.perform()
                    answer_elem = driver.find_element_by_class_name('correct_response')
                    answers.append(answer_elem.text)
            except:
                answers.append('???') # lets us know there is no answer for that question
            index += 1
        else:
            # lets program know there is no valid data found for these clues, answers, and amounts
            clues.append('???')
            answers.append('???')
            amounts.append('???')
        index_entity+=1
    # add final jeopardy content

    final_category = driver.find_element_by_xpath('//table[@class="final_round"]/tbody/tr/td[@class="category"]')
    categories.append(final_category.text)
    final_clue = driver.find_element_by_xpath('//table[@class="final_round"]/tbody/tr/td[@class="clue"]')
    clues.append(final_clue.text)
    final_amount = "Final"
    final_category.click()
    final_answer_elem = driver.find_element_by_class_name('correct_response')
    amounts.append(final_amount)
    answers.append(final_answer_elem.text)
    # create list of dictionaries for each question with values scraped
    full_game = []
    for category, clue, amount, answer in zip(categories,clues,amounts,answers):
        full_game.append({'Category':category,'Amount':amount,'Clue':clue,'Answer':answer})
    
    # convert this list of dictionaries into a datafram object
    df = pd.DataFrame(full_game)
    #print(df)

    play = False # determines if we play the round
    message = (f'Game {numGame} from season {season} is ready for you to play. '
    'Click instructions to learn the mechanics of the game, and whenever you '
    'are ready to start, hit "Play".')
    layout = [
        [sg.Text(message,size=(40,5),font=gameFont,justification='center')],
        [sg.Text(size=(8,1),font=gameFont),sg.Button('Instructions',size=(12,1),font=gameFont),
        sg.Button('Play',size=(12,1),font=gameFont),sg.Text(size=(8,1),font=gameFont)]
    ]
    startWindow = sg.Window('Start Game',layout)
    while True:
        event, values = startWindow.read()
        if event == 'Instructions':
            instructions()
        elif event == 'Play':
            play = True
            startWindow.close()
            break
        elif event == sg.WIN_CLOSED:
            break
    if play:
        jeopardy(0,1,df)

# main code with scoreboard and runs the game
def jeopardy(score,rNum,df): #df as argument, parameter for the round
    title = 'Double Jeopardy Round' if rNum>1 else 'Jeopardy Round'
    half = False
    final = False
    score=score
    offset = ((rNum-1)*30) # offset in the dataframe based on the round
    counter=30*(rNum-1)
    lowValue = offset
    while lowValue<(offset+30):
        if df.iloc[lowValue]['Amount']!='DD' and df.iloc[lowValue]['Amount']!='???':
            break
        lowValue += 1
    lowValue = int(df.iloc[lowValue]['Amount'])
    category_list = [df.iloc[i]['Category'] for i in range(0+offset,6+offset)] # these will come from df
    amount_list = [f'${amount}' for amount in range(lowValue,(lowValue*5+1),lowValue)] #each value times round
    amounts = ['' if df.iloc[i+offset]['Amount'] == '???' else amount_list[int(i/6)] for i in range(0,30)]
    new_amounts = [amount_list[int(i/6)] for i in range(0,30) if df.iloc[i+offset]['Amount'] != '???']
    counter+=30-len(new_amounts)
    layout = [
        [
            sg.Text(title,size=(21,1),font=('Helvetica',20,'bold'),text_color='white'),
            sg.Text(f'Score: {score}',size=(35,1),font=('Helvetica',20,'bold'),
            text_color='white',justification='center',key='score'),
            sg.Button('Next Round',size=(15,1),button_color=('White','Dark Blue'),
            font=('Helvetica',20,'bold'))
        ]
    ]
    categories = [
        [
            sg.Button(category,size=(12,4),button_color=('white','Dark Blue'),
            font=('Helvetica',20,'bold')) for category in category_list
        ]
    ]
    layout += categories
    clues = [
        [
            sg.Button(amounts[col+(row*6)],size=(12,2),button_color=('#ffd300','Dark Blue'),
            font=('Helvetica',20,'bold'),key=(amounts[col+(row*6)]+'-'+str(col))) for col in range(6)
        ] for row in range(5)
    ]
    layout += clues
    window = sg.Window(title,layout)
    new_list = [amounts[col+(row*6)]+'-'+str(col) if amounts[col+(row*6)] != '' else '' for col in range(6) for row in range(5)]
    while True:
        event, values = window.read()
        if event in new_list and event != '':
            window[event].update('')
            new_list.remove(event)
            counter+=1
            # logic for daily double check
            index = grabEvent(event,lowValue)
            clue = df.iloc[index+offset]['Clue']
            answer = df.iloc[index+offset]['Answer']
            amount = df.iloc[index+offset]['Amount']
            if amount == 'DD':
                value = dailyDouble(score,rNum)
                score += doubleClue(clue,value,answer)
                # put afterResponse here
            else:
                value = int(amount)
                score += showClue(value,clue,answer)
            window['score'].update(f'Score: {score}')
            if counter==30:
                half = True
                break
            elif counter==60:
                final = True
                break
        elif event == 'Next Round':
            if(rNum>1):
                window.close()
                finalJeopardy(score,df)
            else:
                window.close()
                halftime(score,df)
        elif event == sg.WIN_CLOSED:
            break
    if half:
        window.close()
        halftime(score,df)
    elif final:
        window.close()
        finalJeopardy(score,df)

# shows clue with countdown to buzz in
def showClue(value,clue,answer): # probably pass df as argument here
    clock = 10
    attempt = False
    extra_lines = 0 # in case of newline characters
    for char in clue: # add lines to accomodate newline characters
        if char == '\n':
            extra_lines += 1
    
    layout = [
        [
            sg.Text(f'Timer: {clock} seconds',size=(40,1),font=gameFont,
            justification='center',key='timer')
        ],
        [
            sg.Text(clue,size=(40,(int)(len(clue)/40)+1+extra_lines),font=gameFont,
            justification='center')
        ],
        [
            sg.Text('Hit the space bar to buzz in.',size=(40,1),font=gameFont,
            text_color='#ffd300',justification='center',key='space')
        ]
    ]
    clueWindow = sg.Window('Clue',layout,return_keyboard_events=True) #make the window name dynamic
    clueWindow.Finalize()
    clueWindow.TKroot.focus_force()
    while clock>0:
        event, values = clueWindow.read(timeout=1000)
        if event == ' ':
            #open new window
            attempt = True
            break
        elif event == sg.WIN_CLOSED:
            clueWindow.close()
            break
        clock-=1
        clueWindow['timer'].update(f'Timer: {clock} seconds')
    if(attempt):
        clueWindow.close()
        response = answerWin(clue)
        if checkAnswer(response,answer):
            afterResponse(response,answer)
            return value
        else:
            afterResponse(response,answer)
            return -value
        # return score
    else:
        afterResponse('',answer)
        clueWindow.close()
        return 0

# gets user input for answer
def answerWin(clue): #pops up window for user to enter answer and returns this answer
    clock = 10 # 10 second countdown upon opening window
    layout = [
        [sg.Text(f'Timer: {clock} seconds',key='timer',font=gameFont)],
        [sg.Text(clue,size=(40,(int)(len(clue)/40)+1),font=gameFont)],
        [
            sg.Text('What is: ',font=gameFont),sg.In(size=(25,1),font=
            gameFont,focus=True),sg.Submit(size=(10,1),font=gameFont)
        ]
    ]
    answerWindow = sg.Window('Answer',layout)
    while clock>0:
        event, values = answerWindow.read(timeout=1000)
        if event == 'Submit':
            if values[0]:
                answerWindow.close()
                return values[0]
        elif event == sg.WIN_CLOSED:
            break
        clock -= 1
        answerWindow['timer'].update(f'Timer: {clock} seconds')
    answerWindow.close()
    return ''

# checks if user response equals answer or is close to it
def checkAnswer(response, answer):
    response = response.lower()
    answer = answer.lower()
    if response == answer:
        return True
    elif len(response)>3 and response in answer:
        return True
    elif answer in response:
        return True
    return False

# informs user their answer was correct or incorrect
def afterResponse(response,answer):
    if checkAnswer(response, answer):
        title = 'Correct!'
        message = (f'{title} You got the correct answer of:')
    else:
        title = 'Sorry.'
        message = (f'{title} The correct answer is:')
    layout = [
        [sg.Text(message,size=(42,1),font=gameFont,justification='center')],
        [sg.Text(f'"{answer}"',size=(42,1),font=gameFont,justification='center')],
        [
            sg.Text(size=(16,1),font=gameFont),sg.Button('Continue',font=gameFont,
            size=(10,1)),sg.Text(size=(16,1),font=gameFont)
        ]
    ]
    window = sg.Window(title,layout)
    while True:
        event, values = window.read()
        if event == 'Continue' or event == sg.WIN_CLOSED:
            window.close()
            break
    #create new window to show the answer

# returns the index of the clue in the dataframe
def grabEvent(text,lowValue):
    newText = text.split('-',1)
    money = int(newText[0][1:])
    money /= (lowValue)
    money = int(money)
    col = int(newText[1])
    index = (money-1)*6+col
    return index

# get user wager on daily double
def dailyDouble(score,rNum):
    message=f'Your score is {score}, and you can risk up to {max(rNum*1000,score)}.'
    layout = [
        [sg.Text('You just found a Daily Double!',size=(25,1),font=gameFont)],
        [sg.Text(message,size=(25,2),font=gameFont,justification='center')],
        [
            sg.Text('Enter a value to wager:',size=(13,2),font=gameFont),
            sg.In(size=(6,1),font=gameFont),sg.Submit(size=(6,1),font=gameFont)
        ]
    ]
    dailyWindow = sg.Window('Daily Double!',layout)
    while True:
        event, values = dailyWindow.read()
        if event == 'Submit':
            if values[0]:
                if(inputValidation(values[0])):
                    wager = int(values[0])
                    if wager<=score or wager<=(1000*rNum):
                        dailyWindow.close()
                        return wager
        elif event == sg.WIN_CLOSED:
            return 0
            break

# separate clue window because for DD user must incur penalty for not answering
def doubleClue(clue,value,answer):
    clock = 25 # 10 second countdown upon opening window
    layout = [
        [sg.Text(f'Timer: {clock} seconds',key='timer',font=gameFont)],
        [
            sg.Text(clue,size=(40,(int)(len(clue)/40)+1),font=gameFont,
            justification='center')
        ],
        [
            sg.Text('What is:',font=gameFont),sg.In(size=(25,1),font=gameFont,
            focus=True),sg.Submit(size=(10,1),font=gameFont)
        ]
    ]
    answerWindow = sg.Window('Answer',layout)
    while clock>0:
        event, values = answerWindow.read(timeout=1000)
        if event == 'Submit':
            if values[0]:
                response = values[0]
                answerWindow.close()
                if checkAnswer(response,answer):
                    afterResponse(response,answer)
                    return value
                else:
                    afterResponse(response,answer)
                    return -value
        elif event == sg.WIN_CLOSED:
            break
        clock -= 1
        answerWindow['timer'].update(f'Timer: {clock} seconds')
    answerWindow.close()
    afterResponse('No answer',answer)
    return -value

# window that gives user a break between Jeopardy and Double Jeopardy Rounds
def halftime(score,df):
    message = (f"It's halftime! Your score at the half is {score}. Click 'Next'"
    " to proceed to Double Jeopardy.")
    layout = [
        [sg.Text(message,size=(24,4),font=gameFont,justification='center')],
        [
            sg.Text(size=(8,1),font=gameFont),sg.Button('Next',size=(8,1),
            font=gameFont),sg.Text(size=(8,1),font=gameFont)
        ]
    ]
    window = sg.Window('Halftime',layout)
    event, values = window.read()
    double = False
    while True:
        if event == 'Next':
            double = True
            window.close()
            break
        elif event == sg.WIN_CLOSED:
            break
    if double:
        jeopardy(score,2,df)

# get user wager for Final Jeopardy based on category
def finalWager(score,category): #df as argument
    layout = [
        [
            sg.Text(f'Your score heading into final: {score}',size=(32,1),
            font=gameFont,justification='center')
        ],
        [
            sg.Text("Here is the Category for final:",size=(32,1),font=gameFont,
            justification='center')
        ],
        [
            sg.Text(f'{category}',size=(32,int(len(category)/32)+1),font=gameFont,
            justification='center',text_color=('yellow'))
        ],
        [
            sg.Text('Enter a wager for this category:',size=(32,1),font=gameFont,
            justification='center')
        ],
        [
            sg.Text(size=(8,1),font=gameFont),sg.In(size=(8,1),font=gameFont,focus=True),
            sg.Submit(size=(8,1),font=gameFont),sg.Text(size=(8,1),font=gameFont)
        ]
    ]
    finalWagerWin = sg.Window('Final Wager',layout)
    while True:
        event, values = finalWagerWin.read()
        if event == 'Submit':
            if values[0]:
                wager = int(values[0])
                if wager <= score and wager>=0:
                    finalWagerWin.close()
                    return wager
                elif score < 0:
                    finalWagerWin.close()
                    return 0
        elif event == sg.WIN_CLOSED:
            return 0

# show final jeopardy clue and get answer
def finalJeopardy(score,df):
    clue = df.iloc[60]['Clue']
    category = df.iloc[60]['Category']
    answer = df.iloc[60]['Answer']
    wager = finalWager(score,category)
    clock = 45 # give the user 45 seconds to answer the question
    layout = [
        [
            sg.Text(f'Timer: {clock} seconds',size=(40,1),font=gameFont,
            justification='center',key='timer')
        ],
        [
            sg.Text(f'{category}',size=(40,int(len(category)/40)+1),font=gameFont,
            justification='center',text_color=('yellow'))
        ],
        [
            sg.Text(clue,size=(40,(int)(len(clue)/40)+1),font=gameFont,
            justification='center')
        ],
        [
            sg.In(focus=True,font=gameFont,size=(32,1)),sg.Submit(size=(8,1),
            font=gameFont)
        ]
    ]
    finalWindow = sg.Window('Final Jeopardy',layout)
    keepGoing = True
    answered = False
    while clock>0:
        event, values = finalWindow.read(timeout=1000)
        if event == 'Submit':
            if values[0]:
                # logic for whether the clue was right or wrong
                response = values[0]
                answered = True
                if checkAnswer(response,answer):
                    score += wager
                    afterResponse(response,answer)
                else:
                    score -= wager
                    afterResponse(response,answer)
                break
        elif event == sg.WIN_CLOSED:
            keepGoing = False
            break
        clock-=1
        finalWindow['timer'].update(f'Timer: {clock} seconds')
    if not answered:
        score -= wager
    finalWindow.close()
    if keepGoing:
        playAgain(score)

# display 'thanks', final score, and ask user if they want to play again
def playAgain(score):
    message = f'Thanks for playing Jeopardy! Your final score was {score}'
    nextGame = "If you would like to play another game, simply hit 'Play Again'"
    layout = [
        [sg.Text(message,size=(32,2),font=gameFont,justification='center')],
        [sg.Text(nextGame,size=(32,2),font=gameFont,justification='center')],
        [
            sg.Button('Play Again',size=(16,1),font=gameFont),sg.Button('Exit',size=(16,1),font=gameFont)
        ]
    ]
    play = sg.Window('Thanks for playing!',layout)
    again = False
    while True:
        event, values = play.read()
        if event == 'Play Again':
            play.close()
            again = True
            break
        elif event == 'Exit' or event == sg.WIN_CLOSED:
            play.close()
            break
    if again:
        getSeason()

getSeason()
driver.quit()