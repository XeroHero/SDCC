#!/bin/bash
# install_cloner.sh
sudo apt update
sudo apt install -y python3-rpi.gpio rsync gdisk dosfstools ntfs-3g exfatprogs

# Copy the cloner script
sudo cp sd_cloner.py /usr/local/bin/
sudo chmod +x /usr/local/bin/sd_cloner.py

# Create systemd service
sudo tee /etc/systemd/system/sd-cloner.service > /dev/null <<EOF
[Unit]
Description=Headless SD Card Cloner
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/sd_cloner.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
sudo systemctl daemon-reload
sudo systemctl enable sd-cloner.service
sudo systemctl start sd-cloner.service

echo "Installation complete!"
echo "Service will start automatically on boot"