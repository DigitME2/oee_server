from app.extensions import celery_app

@celery_app.task
def task2():
    print("running task 2")
    return