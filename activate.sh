export PATH="/srv/nextcloud-appstore/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate venv
export DJANGO_SETTINGS_MODULE=nextcloudappstore.settings.production
