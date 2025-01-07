# no-dog-zone
Train your dog off of areas!

Ever wanted to train your dog to stop getting on the couch?

This is the place for you.

This application will detect that you're dog is on the couch and make a loud noise to get the dog off. You'll also get a video of the event.

It will avoid making any noise if it sees you and it's completely private!

# Current state of the project
This is the very initial stage of the project. In order for this to become a plug and play solution there is lots of work to be done, but if you're a technical person you should be able to get this to work.

I've successfuly trained my dog with this app.

# My setup:
1. A Raspberry Pi 3B
2. A USB camera with night vision ([Arducam 1080P with IR LEDs](https://www.amazon.com/gp/product/B0829HZ3Q7/ref=ppx_yo_dt_b_asin_title_o00_s00?ie=UTF8&psc=1))
3. A buzzer which works with 3.3V, connected to GPIO21 on the Raspberry Pi
Obviously, other setups can also work.

# Instructions
Since I don't know if anyone will use this project I don't want to waste time writing very detailed instructions. If you want to use this, please feel free to [ping me](https://twitter.com/omer_bartal) and I'll gladly add better instructions.

Meanwhile, the general idea is:
- Install `pipenv`, `tmux` and `curl`
- Clone the project
- Run `./install.sh`
  - It will download the model
  - Install dependecies
  - It will tell you how to run the project at boot (a bit of a lazy way for now)
- Telegram related (optional, if you want to get a video recording of what was detected)
   - Create a Telegram bot
   - Create a group with you and the bot
   - Send a direct message to the bot
   - `pipenv run ./params.py -s 'telegram_token="<your bot token\>"'`
   - Run `pipenv run ./telegram_bot.py -u`
   - `pipenv run ./params.py -s 'telegram_admin=<your personal id\>'`
   - `pipenv run ./params.py -s 'telegram_chat_id=<group id\>'`
- Configure area of intereset
  - Run the app (reboot or it using `pipenv run ./app.py --src v4l2 --dst output --params params.json --log output/dog_detect.log -v`)
  - Connect to `http://<ip addr>:8000/`
    (You can get the IP address using the telegram bot by pressing the `IP` button)
- Calibrating the inference (optional):
  - This one is harder to explain. Ping me and I'll add more instuctions. 
- Done!

# Contributing
This is a very new project. I've never managed an open source project so any help would be great, even managing contributions and building procedures would be helpful.

Please feel free to [contact me directly](https://twitter.com/omer_bartal) if you're interested. That's the best way to show interest in the project :)

The nice thing about this project is that it can turn into anything which meets the definition:

detect something using a pretrained model --> do something with hardware

I've started a todo list under the [`CONTRIBUTING`](CONTRIBUTING.md) file.
