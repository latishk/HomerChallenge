# Author: Latish Khubnani
# Date: Fri Feb 10 2017

from ast import literal_eval
from datetime import datetime as dt
from plotly import tools
import numpy as np
import pandas as pd
import pymongo
import pickle
import plotly as py
import plotly.graph_objs as go

mongo_db = { 'host': 'localhost', 'port': 27017, 'db': 'Homer', 'collection': 'DataEngineerSampleData' }
client = pymongo.MongoClient(mongo_db['host'], mongo_db['port'])
db = client[mongo_db['db']]
collection = db[mongo_db['collection']]


def processData(collection_name):
    """
    This function reads the huge text file line by line and stores the dictionary in the database after adding
    date fields.
    :param collection_name: string
    """
    if not isinstance(collection_name, str):
        print("Invalid name, using the string conversion of passed parameter")
        collection_name = str(collection_name)

    global collection, db, mongo_db
    collection = db[mongo_db[collection_name]]
    days = { 0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday" }
    var = 0
    with open('DataEngineerSampleData.txt', encoding='utf-8') as f:
        for i in f:
            record = literal_eval(i.rstrip())
            dateTime = dt.fromtimestamp(record['_t'])
            record['Year'] = dateTime.date().year
            record['Month'] = dateTime.date().month
            record['Day'] = dateTime.date().day
            record['Week'] = dateTime.date().isocalendar()[1]
            record['DayOfWeek'] = days[dateTime.date().weekday()]
            record['Hour'] = dateTime.time().hour
            record['Minutes'] = dateTime.time().minute
            collection.insert(record)
            del record

            # if you want to test the output with 100,000 records
            # var += 1
            # if var > 100000:
            #     break


def most_common_events(number_of_events=4):
    """
    Finds the most occuring events and prints the results in form of data frame.
    :param number_of_events: Get top most occuring events during the sessions
    :return: Graph object trace
    """
    pipeline = [
        { "$group": { "_id": "$_n", "count": { "$sum": 1 } } },
        { "$sort": { 'count': -1 } }
    ]

    event_counts = list(collection.aggregate(pipeline))
    event_counts.sort(key=lambda x: x['count'], reverse=True)
    if len(event_counts) > number_of_events:
        event_counts = event_counts[0:number_of_events]

    output = open('A1.pkl', 'wb')
    pickle.dump(event_counts, output)
    output.close()
    event_counts = pd.DataFrame(event_counts)
    event_counts.rename(columns={ "_id": "Event Type" }, inplace=True)
    event_counts = event_counts[event_counts["Event Type"].notnull()]
    print("\n",event_counts)
    trace1 = go.Bar(x=event_counts["Event Type"], y=event_counts['count'])
    # py.offline.plot([trace1])
    return trace1


def most_read_title(top_x=5):
    """
    Function to query the mongo database to find most read titles and prints the results in form of data frame
    :param top_x: Top 'x' most read Titles, default Top 5 most read titles
    :return: Graph Object Trace
    """
    most_read_title_pipeline = [
        { "$match": { "_n": "open" } },
        { "$group": { "_id": "$manuscripttitle", "count": { "$sum": 1 } } },
        { "$sort": { 'count': -1 } }
    ]

    most_read_title_results = list(collection.aggregate(most_read_title_pipeline))
    most_read_title_results.sort(key=lambda x: x['count'], reverse=True)
    if len(most_read_title_results) > top_x:
        most_read_title_results = most_read_title_results[0:top_x]

    print("\n Most read title results:\n",most_read_title_results)

    output = open('A2.pkl', 'wb')
    pickle.dump(most_read_title_results, output)
    output.close()

    most_read_title_results = pd.DataFrame(most_read_title_results)
    most_read_title_results.rename(columns={ "_id": "Lesson Title" }, inplace=True)
    # py.offline.plot([])
    trace = go.Bar(x=most_read_title_results["Lesson Title"], y=most_read_title_results["count"])

    print("\n",most_read_title_results)

    return trace


def get_user_stats( user_id="V0DHBMUYQI"):
    """

    :param user_id: User Idenfication Alpha numeric string.
    """
    # "_n": { "$in": ["open", "complete", "incomplete"] }
    user_activity = list(collection.find({ "_p": user_id },
                                         { "_n": 1, "_p": 1, "_t": 1, "manuscriptid": 1, "Hour": 1, "Minutes": 1,
                                           "Day": 1, "Week": 1, "Month": 1, "Year": 1 }))
    df = pd.DataFrame(user_activity)
    df = df.drop_duplicates(subset=["_n", "_t"])

    # Approach 1
    # Here we are calculating the time between the current event and the next one, an open event followed by opening the
    # menu will lead to recording the time till when the lesson was open i.e till when it was read. Here The key is that
    # anything different event followed by open means the user has stopped reading. so we don't need to find
    # corresponding 'complete' or incomplete tag to calculate the time spent. Later we just group it by day, week and
    # month and find mean. I guess this might be a problem in case of no event recorded and user closes the app.(?)

    # Approach 2
    # according to problem statement we need to look for open along with complete / incomplete to check for total time
    # spent to complete the lesson. for that we will group by manuscript id and remove the duplicates then subtract the
    # time for that group from next record.

    df = df[df["_n"].isin(["open", "complete", "incomplete"])]
    df["timeSpent"] = [dt.fromtimestamp(x) for x in df["_t"]]
    grouped_df = df.groupby('manuscriptid')["timeSpent"].apply(lambda x: x - x.shift())
    df["timeSpent"] = grouped_df.fillna(0)
    df["timeSpent"] = [np.abs(x.total_seconds()) / (60 * 60) for x in df["timeSpent"]]

    # print(grouped_df)
    # print(df)

    df.rename(columns={ 'timeSpent': "Minutes Spent" }, inplace=True)
    average_day_time_spent = pd.pivot_table(df, index=["Day", "Month", "Year"], values=["Minutes Spent"],
                                            aggfunc=[np.mean])

    average_month_time_spent = pd.pivot_table(df, index=["Month", "Year"], values=["Minutes Spent"],
                                              aggfunc=[np.mean])
    average_week_timespent = pd.pivot_table(df, index=["Week", "Year"], values=["Minutes Spent"],
                                            aggfunc=[np.mean])

    print("Average time spent by days", average_day_time_spent, "\n\nAverage time spent by Week", average_week_timespent,
          "\n\nAverage time spent by Month", average_month_time_spent)

    output = open('A3.pkl', 'wb')
    pickle.dump(df, output)
    output.close()


    # all_plots = go.bar(average_day_time_spent)


def main():
    Events = most_common_events(4)
    Titles = most_read_title(5)

    fig = tools.make_subplots(rows=2, cols=1, subplot_titles=('1. Most Occuring Events', '2. Most Read Titles'))
    fig.append_trace(Events, 1, 1)
    fig.append_trace(Titles, 2, 1)
    fig['layout'].update(title='Challenge Answers', showlegend=False)
    py.offline.plot(fig)

    print("For User IHL8FBBKTB")
    get_user_stats("IHL8FBBKTB")


if __name__ == '__main__':
    main()


    # most occuring users
    # 0  IHL8FBBKTB  52861
    # 1  V0DHBMUYQI  51425
    # 2  JBMU3E6QRD  34759
    # 3  NPL04PA1NT  31596
    # 4  FZQM7F3WQU  30759
    # 5  FZGCAHO857  28796
    # 6  9PEE7EACG9  26288
    # 7  Z6JNHVGMFP  25354
    # 8  2PEP2P4NGD  22478
    # 9  084RJU8BZK  19157
    

# 4. To create Database suitable for this data, SQL Database seems fit. I will make separate table for users with primary key being "userid" values along with email_id,
# screenname, age,  etc details about the user.The activity table will be separate table with key being autoincrementing index, this will have timestamp, userid, manuscript id, date, time, event type and capaign details.
# Userid, manuscriptid will be foriegn keys. Database for manuscripts containing their ids, titles and other details witll be made.






