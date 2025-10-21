rm -f /etc/systemd/uwsgi-appstore.service
cp uwsgi-appstore.service /etc/systemd/system/uwsgi-appstore.service
systemctl daemon-reload
systemctl enable --now uwsgi-appstore.service & systemctl restart uwsgi-appstore.service
systemctl status uwsgi-appstore.service
