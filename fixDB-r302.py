import sqlite3

def addColumn(table, column, type="NUMERIC", default=0):

    connection = sqlite3.connect("sickbeard.db")
    connection.row_factory = sqlite3.Row
    
    try:
        print "Adding", column, "column to", table, "table"
        sql = "ALTER TABLE " + table + " ADD " + column + " " + type
        print sql
        connection.execute(sql)
        sql = "UPDATE " + table + " SET " + column + "=" + str(default)
        print sql
        connection.execute(sql)
        connection.commit()
    except sqlite3.DatabaseError, e:
        print "Fatal error executing query '" + sql + "': " + str(e)
        raise

addColumn("tv_shows", "tvr_name", "TEXT", "")