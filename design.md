### 汇率机制
写一个脚本将汇率存入redis缓存中，然后每隔5小时请求更新一次

数据库连接：
进入docker的postgresql命令行：
docker exec -it postgres16 bash

psql -U postgres -d mydb

重启fastapi服务：
sudo systemctl restart fastapi.service
sudo systemctl status fastapi.service

查看实时日志:
sudo journalctl -u fastapi.service -f