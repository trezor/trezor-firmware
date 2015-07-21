# initialize from the image

FROM fedora:21

# update package repositories

RUN yum install -y deltarpm yum-plugin-fastestmirror
RUN yum update -y

# install tools

RUN yum install -y cmake make wget
RUN yum install -y gcc gcc-c++ git make patchutils pkgconfig wget

# install dependencies for Linux packaging

RUN yum install -y ruby-devel rubygems rpm-build
RUN gem install fpm --no-document

# install dependencies for Linux build

#RUN yum install -y glibc-devel glibc-static libgcc libstdc++-static zlib-devel
#RUN yum install -y boost-static libusbx-devel protobuf-static

#RUN yum install -y glibc-devel.i686 glibc-static.i686 libgcc.i686 libstdc++-static.i686 zlib-devel.i686
#RUN yum install -y boost-static.i686 libusbx-devel.i686 protobuf-static.i686

# protobuf-static does not install protobuf-devel, workaround

#RUN yum install -y protobuf-devel

# install used networking libraries

#RUN yum install -y libcurl-devel libmicrohttpd-devel
#RUN yum install -y libcurl-devel.i686 libmicrohttpd-devel.i686
