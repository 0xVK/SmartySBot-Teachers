#!/bin/bash
	ret=$(ps aux | grep "SmartySBot.py" | wc -l)
	if [ "$ret" -eq 1 ]
then {
	source /root/virt_env/bin/activate
	nohup python3 /root/SmartySBot/SmartySBot.py &
	exit 1
}
else
{
	exit 1
}
fi;

