if [ ! -f /appdata/ ]; then
    echo "Making appdata directory"
    mkdir /appdata
fi

if [ ! -f /appdata/config.py ]; then
    echo "copying config file to volume"
    cp /home/appdata_template/config.py /appdata/config.py
fi

if [ ! -f /appdata/static/ ]; then
    echo "copying static folder to volume"
    cp -r /home/appdata_template/static /appdata
fi