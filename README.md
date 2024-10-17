# OpenSQL Install Packager

OpenSQL 컴포넌트(PostgreSQL, pgpool, postgis, barman) 설치 파일 종합 패키징 툴입니다.

## feature

- OpenSQL을 설치하려는 os 종류 및 버전에 알맞는 설치 필수 파일과 더불어 설치 의존성 파일들을 모두 패키징하여, 외부(인터넷) 접속이 안되는 os 환경에서도 설치가능한 opensql 패키지를 생성합니다.

- 해당 툴을 통해 생성된 OpenSQL 설치 패키지는 `opensql.tar` 라는 한 개의 tar 압축 형태로 제공되며, 압축 해제 시 각 컴포넌트 설치에 필요한 파일들이 컴포넌트 디렉토리 별로 분류되어 첨부되어 있습니다.

## 사용법

### 요구사항

해당 툴을 사용하기 앞서, 다음 요소들이 툴을 사용하려는 머신에 설치되어 있어야 합니다.

- Python3 + pip (툴 개발은 Python 3.12.3 버전에서 진행되었습니다.)
- docker

### 구성요소

툴은 다음과 같은 구성요소로 이루어져 있습니다.

- `logs` (디렉토리) : 툴 실행 시 사용된 도커 컨테이너 내부 로그를 기록합니다. (툴 실행 시 디렉토리 및 로그파일이 자동 생성됩니다.)
- `input.yaml` : OpenSQL 패키징 설정 파일입니다.
- `package.py` : 툴 수행동작을 기술한 파이썬 스크립트입니다.
- `requirements.txt` : 툴 사용에 필요한 파이썬 요구 라이브러리 모음입니다.

### 초기 세팅

툴을 사용하려는 환경에서 최초로 한 번 설정해주는 세팅 작업입니다.

다음 명령을 실행하여, 툴 내부에서 필요로 하는 외부 라이브러리 세팅을 진행합니다.

```
pip install -r requirements.txt
```

설치 후 `pip list`를 통해 아래와 같은 라이브러리들이 설치되었는지 확인합니다.

```
$ pip list
Package            Version
------------------ ---------
certifi            2024.8.30
charset-normalizer 3.3.2
docker             7.1.0
idna               3.10
pip                24.0
PyYAML             6.0.2
requests           2.32.3
urllib3            2.2.3
```

### 패키지 세팅

매번 OpenSQL 패키지를 생성하기 전, `input.yaml` 를 수정하여 OpenSQL 패키지를 설치하고자 하는 os 종류 및 버전을 지정합니다.

`input.yaml`은 다음과 같습니다.
```yaml
os:
  name: oraclelinux
  version: 8.10
# available os: {
#   oraclelinux: [ 8.0 ~ 8.10, 9 ]
#   rockylinux: [ 8.4 ~ 8.10, 9.0 ~ 9.4 ]
# }

database:
  name: postgresql
  version: 15.8
# available version: [ 15.8 ]

options:
  - name: pgpool
    version: 4.4.4
    # available version: [ 4.4.4 ]

  - name: postgis
    version: 3.4.0
    # available version: [ 3.4.0 ]

  - name: barman
    version: 3.11.1
    # available version: [ 3.11.1 ]

```

위 디폴트 세팅은 생성될 opensql.tar 패키지가 oraclelinux의 8.10 버전에서 설치가능하며, postgresql 15.8 버전, pgpool 4.4.4 버전, postgis 3.4.0 버전, barman 3.11.1 버전의 컴포넌트를 설치할 수 있음을 나타냅니다.

주석은 현재 툴에서 지원되는 os 및 OpenSQL 컴포넌트 버전을 기재하고 있습니다.

추후 필요에 따라 지원 가능한 버전은 추가될 수 있습니다.


### 패키지 생성 실행

위 input.yaml 설정이 끝나면, 다음과 같이 실행하여 OpenSQL 설치 패키지 생성을 실행합니다.

```
python3 package.py
```

패키지 생성은 하드웨어 성능에 따라 다르나 대략 5분 정도의 시간이 소요되며, 툴 실행이 완료되면 `opensql.tar` 패키지가 생성됩니다.

## 생성된 OpenSQL 설치 패키지

툴 실행이 완료되면 `opensql.tar` 라는 tar 압축 형태로 제공되며, 압축 해제 시 설치에 필요한 파일들이 컴포넌트별로 분류 및 첨부되어 있습니다.

os 종류 및 버전에 따라 각기 다른 opensql.tar 설치 패키지를 생성하므로, 설치하고자 하는 os 종류와 버전에 알맞는 opensql.tar 를 활용하여 OpenSQL 설치를 진행해야 합니다.

아래는 opensql.tar 패키지 설치 방법 및 구성에 대한 설명입니다

### 구성요소

`tar -xvf opensql.tar` 명령을 통해 압축 해제를 진행하면 `opensql` 디렉토리가 생성되는 것을 확인할 수 있습니다.

`opensql` 디렉토리 내부에는 다음과 같은 파일들을 포함하고 있습니다.


* `METADATA` 현재 opensql.tar 패키지에 포함된 구성요소 및 버전정보를 기술한 메타데이터
* `postgresql` 설치를 위한 패키지파일 모음 디렉토리
* `pgpool` 설치를 위한 패키지파일 모음 디렉토리
* `postgis` 설치를 위한 패키지파일 모음 디렉토리
* `barman` 설치를 위한 패키지파일 모음 디렉토리


`METADATA`

이 opensql.tar를 설치 가능한 OS 및 버전이 무엇인지, 또 설치가능한 패키지들이 어떤 버전으로 해당 opensql.tar에 포함되어 있는지 기술한 명세서 입니다.

내용 예시는 아래와 같습니다

```bash
[root@1707c7ea4ee0 opensql]# cat METADATA 

# oraclelinux 8.10에서 아래 패키지들이 설치 가능함을 나타냅니다
[SUPPORTED OS VERSION]
oraclelinux 8.10

# 현재 tar에 포함되어 있는 설치 가능한 구성 패키지들 목록입니다.
[INSTALLABLE BINARIES]
postgresql 15.8
pgpool 4.4.4
postgis 3.4.0
barman 3.11.1

[root@1707c7ea4ee0 opensql]#
```

위 예시의 경우, 해당 opensql.tar 패키지가 oraclelinux의 8.10버전에서 이용가능하며, postgresql 15.8 버전, pgpool 4.4.4 버전, postgis 3.4.0 버전, barman 3.11.1 버전의 컴포넌트를 설치할 수 있음을 나타냅니다.


`postgresql, pgpool, postgis, barman`

설치 가능한 구성요소들의 패키지 파일들을 분류하여 모아놓은 디렉토리들입니다.

**현재 툴에서 지원되는 os는 레드헷 계열의 oraclelinux, rockylinux 이므로 각 컴포넌트의 설치 패키지 파일들은 rpm 파일들로 구성되어 있습니다.**


### 설치 (Oraclelinux, Rockylinux)

redhat 계열 os에 기본 탑재된 `rpm` 명령어를 이용하여 각 구성요소의 rpm 패키지 파일들을 직접 설치합니다.

`opensql` **디렉토리로 이동하여 ,** **다음 형식으로 opensql 패키지 rpm을 설치하면 됩니다.**

* 전체 설치

  `rpm -Uvh --nodeps --replacepkgs --replacefiles ./**/*.rpm`

* 선택 설치

  `rpm -Uvh --nodeps --replacepkgs --replacefiles ./{구성요소 디렉토리 이름}/*.rpm`

  ex) postgresql만 설치할때,

  `rpm -Uvh --nodeps --replacepkgs --replacefiles ./postgresql/*.rpm`


**(단, 위 명령어들은 머신에 이미 동일한 패키지가 설치되어 있으면 교체를 진행하고, 패키지 구성 내용 중 동일한 파일이 존재하면 교체를 진행하면서 rpm 설치를 진행하므로 유의가 필요합니다.)**


**(참고) rpm 명령어 구조**

`rpm {설치옵션} [부가옵션] {설치하려는 rpm 파일의 경로}`

* 설치 옵션
  * 신규 설치 `-ivh` : rpm이 이미 설치가 되어 있으면 설치 안함
  * 업그레이드 `-Uvh` : rpm이 이미 설치 되어 있으면 더 최신 버전일 경우 설치 진행
* 부가 옵션
  * `--nodeps` : rpm 설치 시 기본적으로 의존성 rpm 유무 체크하고 없으면 설치 중단하는데, 이 옵션 추가 시 의존성 체크를 하지 않고 rpm 설치 진행하도록 함
  * `--replacepkgs` : 이미 동일한 버전의 패키지가 설치되어 있으면 rpm 설치를 거부하는데, 이 옵션 추가 시 rpm 패키지를 교체하면서 설치 진행하도록 함
  * `--replacefiles` : 이미 설치된 패키지의 구성 파일과 겹치는 구성 파일이 있으면 rpm 설치를 거부하는데, 이 옵션 추가 시 구성파일을 교체하면서 설치 진행하도록 함

## 기타

opensql.tar 패키지는 OpenSQL 컴포넌트를 설치하는 작업만 포함되었으므로, 각 구성요소의 설치가 완료되면 해당 컴포넌트의 설정(postgresql init, pgpool backend conf 설정 등..)은 직접 진행해주셔야 합니다.