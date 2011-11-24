import datetime

yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
last_month = datetime.datetime.utcnow() - datetime.timedelta(days=30)
last_year = datetime.datetime.utcnow() - datetime.timedelta(days=365)

def update_common(obj, report):
    """ do updated_at and sourceless checks """
    # updated checks
    if obj['updated_at'] >= yesterday:
        report['_updated_today_count'] += 1
        if obj['updated_at'] >= last_month:
            report['_updated_this_month_count'] += 1
            if obj['updated_at'] >= last_year:
                report['_updated_this_year_count'] += 1


    # sources
    if not obj['sources']:
        report['sourceless_count'] += 1
