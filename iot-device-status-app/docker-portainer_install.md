docker portainer使用教程
首先确保已经安装了docker.io

```
docker ps 
```

 #查看
若无就安装docker

```
sudo apt install docker
```

ubuntu中配置源，其他的源需要登录
创建daemon.json

```dart
vim /etc/docker/daemon.json
```

添加源

```
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.mybacc.com",
    "https://dytt.online",
    "https://lispy.org",
    "https://docker.xiaogenban1993.com",
    "https://docker.yomansunter.com",
    "https://aicarbon.xyz",
    "https://666860.xyz",
    "https://docker.zhai.cm",
    "https://a.ussh.net",
    "https://hub.littlediary.cn",
    "https://hub.rat.dev",
    "https://docker.m.daocloud.io"
  ]
}
```
```
sudo systemctl restart docker
```
```
docker run -d   -p 9000:9000   -p 9443:9443   --name portainer   --restart=always   -v /var/run/docker.sock:/var/run/docker.sock   -v portainer_data:/data   portainer/portainer-ce
```
也可以先拉取再运行

```dart
docker pull portainer/portainer-ce
```

```dart
docker run -d   -p 9000:9000   -p 9443:9443   --name portainer   --restart=always   -v /var/run/docker.sock:/var/run/docker.sock   -v portainer_data:/data   portainer/portainer-ce
```
注意：

```dart
docker run -d   -p 9000:9000   -p 9443:9443   --name portainer     portainer/portainer-ce
```

若只有这些，本地的其他容器就看不见了，
可以先停掉现有portainer容器，然后再启动
