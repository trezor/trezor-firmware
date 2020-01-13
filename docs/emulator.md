#  使用docker 运行trezor 模拟器

## 安装`docker`
   
  https://docs.docker.com/install/

## Download image

 docker pull bixin/trezor_emu

##  Linux 使用docker 运行trezor 模拟器

 ```
 docker run -it --rm -e DISPLAY=$DISPLAY  -v /tmp/.X11-unix:/tmp/.X11-unix -v /<terzor.elf path>/firmware:/data --volume /tmp/.X11-unix:/tmp/.X11-unix --privileged --network=host lightningcn/trezor_emu:latest /data/trezor.elf
 ```

##  Mac 使用docker 运行trezor 模拟器

- 安装[XQuartz](https://www.xquartz.org/releases/XQuartz-2.7.8.html)，版本必须是`2.7.8`
- 启动`XQuartz`，点击`偏好设置` ,然后点击`安全` 勾选该面板下的两个单选框，然后重启`XQuartz`
- 设置环境变量IP `export IP=$(ifconfig en0 | grep inet | awk '$1=="inet" {print $2}')` 
- 把环境变量`IP`加入到`ACL`，需要`root`权限`sudo /usr/X11/bin/xhost $IP`
- 运行容器`docker run -it --rm -e DISPLAY=$IP:0  -v /tmp/.X11-unix:/tmp/.X11-unix -v （elf可执行文件的本地路径）:/data -p 21324:21324/udp  --privileged  lightningcn/trezor_emu:latest /data/trezor.elf`


## test

###  install python-trezor

   https://wiki.trezor.io/Using_trezorctl_commands_with_Trezor

###  run command

   ```
    trezorctl -p udp get_features
   ```

   ```
    trezorctl --help
   ```
