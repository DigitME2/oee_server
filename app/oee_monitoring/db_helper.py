def start_activity():
    """ Called to begin an activity eg uptime, downtime"""
    job_id = request.form['job_id']
    user_id = request.form['user_id']
    activity_code_id = request.form['activity_code_id']
    timestamp_start = time()
