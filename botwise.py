import csv
import logging
import os
import pathlib
import random
import re
import sqlite3
import sys
import time
from functools import wraps
from typing import List, Union
from urllib.parse import urlencode

import bs4
import crython
import requests

logger = logging.getLogger('botwise')


Question = Union[int, str]


PEERWISE_SCHEDULE = os.environ['PEERWISE_SCHEDULE']
PEERWISE_INSTITUTION = os.environ['PEERWISE_INSTITUTION']
PEERWISE_COURSE = os.environ['PEERWISE_COURSE']
auth = {
    'user': os.environ['PEERWISE_USER'],
    'pass': os.environ['PEERWISE_PASS'],
    'inst_shortcode': PEERWISE_INSTITUTION,
    'cmd': 'login',
}

BASE_URL = 'https://peerwise.cs.auckland.ac.nz'
LOGIN_URL = BASE_URL + '/at/?' + PEERWISE_INSTITUTION
HOME_URL = BASE_URL + '/home/'
COURSE_URL = BASE_URL + '/course/main.php?course_id=' + str(PEERWISE_COURSE)
QUESTION_URL = BASE_URL + '/course/main.php'

DATABASE_PATH = pathlib.Path(os.environ['DATABASE_PATH'])


def log_errors(logger):
    def wrapper(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                logger.exception("Uncaught exception!")
                raise
        return wrapped
    return wrapper


def make_session() -> requests.Session:
    return requests.Session()


def log_in(session, auth):
    session.get(LOGIN_URL, allow_redirects=False).raise_for_status()
    time.sleep(0.5)
    response = session.post(LOGIN_URL, data=auth, allow_redirects=False)
    response.raise_for_status()
    assert response.status_code == 302
    assert response.headers['Location'] == '../home/'

    response = session.get(HOME_URL, allow_redirects=False)
    response.raise_for_status()
    assert response.status_code == 200

    response = session.get(COURSE_URL, allow_redirects=False)
    response.raise_for_status()
    assert response.status_code == 200


def answer_question(session: requests.Session, question: Question):
    question_id, answer_letter = question
    logger.info("Answering question %s with %s", question_id, answer_letter)

    response = session.get(QUESTION_URL, allow_redirects=False, params=[
        ('cmd', 'answerQuestion'),
        ('id', str(question_id)),
    ])
    response.raise_for_status()
    if response.status_code == 302:
        logger.warning("Got a redirect 302 redirect to %s when GETting a question...", response.headers['Location'])
        return False
    elif response.status_code != 200:
        logger.warning("Got a %s response when GETting a question...", response.status_code)
        return False

    soup = bs4.BeautifulSoup(response.text, 'html5lib')
    question_text = soup_text(soup.find(id='questionDisplay'))
    logger.info('Question text: %s', question_text[:200])

    response = session.post(QUESTION_URL, allow_redirects=False, data={
        'answer': answer_letter,
        'cmd': 'saveAnswer',
        'id': str(question_id),
    })
    response.raise_for_status()
    if response.status_code == 302:
        logger.warning("Got a redirect 302 redirect to %s when posting an answer...", response.headers['Location'])
        return False
    elif response.status_code != 200:
        logger.warning("Got a %s response when posting an answer...", response.status_code)
        return False

    soup = bs4.BeautifulSoup(response.text, 'html5lib')
    all_good = soup.select('td.displayCircleAndHighlightOption')
    if len(all_good):
        logger.info("Answer was correct!")
        return True

    try:
        correct_answer = soup.select('td.displayHighlightOption')[0]
        logger.warning("Author suggests answer to %d is %s", question_id, soup_text(correct_answer))
    except IndexError:
        logger.warning("Wrong answer, and couldn't find the right one!")
    return False


@crython.job(expr=PEERWISE_SCHEDULE, ctx='thread')
@log_errors(logger)
def answer_random_question():
    logger.info("Waking up to answer a random question")
    session = make_session()
    log_in(session, auth)
    logger.info("Logged in")

    with open_database(DATABASE_PATH) as conn:
        while True:
            c = conn.cursor()
            results = c.execute("select * from questions where answered = 0")
            result = results.fetchone()
            if result is None:
                logger.error("Boo, no more questions!")
                break

            question = (result['question_id'], result['answer_letter'])

            correct = answer_question(session, question)
            c.execute(
                "UPDATE questions SET answered = 1, correct = ? WHERE id = ?",
                (correct, result['id']))
            conn.commit()

            if correct:
                logger.info("All done! Sleeping again")
                break
            else:
                logger.info("Answer was wrong! Trying again...")


def test_auth():
    session = make_session()
    log_in(session, auth)
    logger.info("Auth is all good!")


def soup_text(element: bs4.Tag) -> str:
    return normalize_text(''.join(element.strings))



def normalize_text(text: str) -> str:
    text = ' '.join(text.splitlines())
    text = re.sub(r'\s\s+', ' ', text)
    text = text.strip()
    return text


def open_database(path: pathlib.Path):
    create = not path.exists()
    connection = sqlite3.Connection(path)
    connection.row_factory = sqlite3.Row
    if create:
        create_database(connection)
    return connection


def create_database(connection: sqlite3.Connection):
    c = connection.cursor()
    c.execute(
        '''
        create table questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            answer_letter TEXT,
            answered BOOLEAN DEFAULT FALSE,
            correct BOOLEAN NULLABLE DEFAULT NULL,
            created  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')
    connection.commit()


def main():
    logger.info("Starting up!")
    with open_database(DATABASE_PATH) as conn:
        c = conn.cursor()

    test_auth()

    logger.info("Running with schedule '%s'", PEERWISE_SCHEDULE)
    crython.tab.start()
    crython.tab.join()
    logger.info("Closing down!")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
