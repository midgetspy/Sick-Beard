import sqlite3

NEWZBIN = 1
TVBINZ = 2
NZBS = 3
EZTV = 4
NZBMATRIX = 5
TVNZB = 6

histMap = {-1: 'unknown',
           1: 'newzbin',
           2: 'tvbinz',
           3: 'nzbs',
           4: 'eztv',
           5: 'nzbmatrix',
           6: 'tvnzb'}


def fixHistoryTable():

    connection = sqlite3.connect("sickbeard.db")
    connection.row_factory = sqlite3.Row
    
    try:
        sql = "ALTER TABLE history RENAME TO history_old"
        print sql
        connection.execute(sql)
        connection.commit()

        sql = "CREATE TABLE history (action NUMERIC, date NUMERIC, showid NUMERIC, season NUMERIC, episode NUMERIC, quality NUMERIC, resource TEXT, provider TEXT);"
        print sql
        connection.execute(sql)
        connection.commit()

    
    except sqlite3.DatabaseError, e:
        print "Fatal error executing query '" + sql + "': " + str(e)
        raise

def fixHistory(number, name):

    connection = sqlite3.connect("sickbeard.db")
    connection.row_factory = sqlite3.Row
    
    try:

        sql = "SELECT * FROM history_old"
        print sql
        sqlResults = connection.execute(sql).fetchall()
        for curResult in sqlResults:
            sql = "INSERT INTO history (action, date, showid, season, episode, quality, resource, provider) VALUES (?,?,?,?,?,?,?,?)"
            try:
                args = [curResult["action"], curResult["date"], curResult["showid"], curResult["season"], curResult["episode"], curResult["quality"], curResult["resource"], histMap[int(curResult["provider"])]]
            except ValueError:
                continue
            print sql, args
            connection.execute(sql, args)
            connection.commit()

    
    except sqlite3.DatabaseError, e:
        print "Fatal error executing query '" + sql + "': " + str(e)
        raise


fixHistoryTable()
for x in histMap.keys():
    fixHistory(x, histMap[x])