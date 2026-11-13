FROM php:8.3-apache

RUN a2enmod rewrite
WORKDIR /var/www/html

COPY .htaccess /var/www/html/.htaccess
COPY php /var/www/html/php
COPY html /var/www/html/html
COPY css /var/www/html/css
COPY js /var/www/html/js
COPY assets /var/www/html/assets