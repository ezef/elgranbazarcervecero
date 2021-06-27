FROM python:2

RUN apt-get update && apt-get -y install cron

# Copy scrapping-cron file to the cron.d directory
# COPY scrapping-cron /etc/cron.d/scrapping-cron

RUN touch /etc/cron.d/scrapping-cron && echo "0 0 * * SUN root /usr/src/app/scrap.sh" > /etc/cron.d/scrapping-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/scrapping-cron

# Apply cron job
RUN crontab /etc/cron.d/scrapping-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod 0700 scrap.sh

# Run the command on container startup
CMD cron && tail -f /var/log/cron.log

#CMD [ "python", "./scrapper.py" ]

# RUN chmod +x ./docker-entrypoint.sh

# ENTRYPOINT ["./docker-entrypoint.sh"]
