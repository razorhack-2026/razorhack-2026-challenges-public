FROM php:8.2-apache

COPY src/app/public/ /var/www/html/
COPY src/app/classes/ /var/www/classes/

RUN mkdir -p /var/log/rubberstamp \
    && chown -R www-data:www-data /var/log/rubberstamp /var/www/html

EXPOSE 80
