=======
botwise
=======

A bot that can automatically answer a few questions per day on Peerwise for you.

Is this cheating?
=================

This is only built to help earn the
'answer at least one question correctly on 31 different days' badge.
It requires you to enter question IDs and answers before it will submit them.
It doesn't come up with the answers,
or try to brute force the right answer.
You still have to go to the effort of
looking for a question and finding the correct answer.
The only thing this assists with is people who are too busy
to be able to consistently answer questions day after day.

Running the bot
===============

.. code-block:: shell

    $ docker run \
        --rm \
        --env PEERWISE_INSTITUTION=uni_id \
        --env PEERWISE_COURSE=12345 \
        --env PEERWISE_USER=username \
        --env PEERWISE_PASS=password \
        --env DATABASE_PATH=/mnt/questions/questions.db \
        --volume /path/to/questions:/mnt/questions \
        timheap/botwise

To find your institution ID, go to the Peerwise homepage
and find your University in the search box.
This will take you to a log in page.
Look in the URL. Your institution ID is in the query string.

To find the course ID, log in to your account.
Under the 'Your courses' heading, find the course you want to use.
The course ID is under the course title.

By default, the bot will wake up once per day.
You can customise this by setting the ``$PEERWISE_SCHEDULE`` environment variable.
It accepts cron-like expressions.
More specifically, it uses `crython <https://github.com/ahawker/crython>`_ under the hood,
so refer to the crython docs for more information on accepted formats.

When the bot wakes up to answer a question,
it will pick a question from the questions database and submit the answer.
If the answer is correct, it will go back to sleep.
If the answer is incorrect it will try another question
either until it is successful or until it runs out of questions.

If the bot runs out of questions when it wakes up to answer a question,
it will put itself back to sleep.
If you add new questions to the database,
next time it wakes up it will pick one of these new questions.
No need to restart the bot!

Adding questions
================

On first run, the bot will create an sqlite database at ``$DATABASE_PATH``.
You can add questions to this database while the bot is running:

.. code-block:: shell

    $ sqlite3 questions.db
    sqlite> INSERT INTO questions (question_id, answer_letter) VALUES
       ...> (12345, 'A'),
       ...> (23456, 'B');
    sqlite>

Find the question ID in the URL,
and the answer letter is any of five available answer letters
'A', 'B', 'C', 'D', 'E'.
