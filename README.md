# OpenSQL Install Packager

- 특정 OS, PG 버전에 맞추어 OpenSQL 종합 설치 패키지를 생성하는 툴입니다

- 툴이 제공하는 설정파일을 통해 지정한 os 종류 및 버전에 호환 가능한 OpenSQL 컴포넌트 설치 파일 및 의존성 파일들을 모두 패키징하여, 외부(인터넷) 접속이 안되는 os 환경에서도 설치가능한 opensql 패키지를 생성합니다.

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

툴 실행환경에서 최초로 한 번 설정해야 하는 작업입니다.

터미널에서 다음 작업들을 진행합니다

#### python3 라이브러리 설치
```
pip install -r requirements.txt
```

#### python3 라이브러리 설치 확인
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

### OpenSQL 패키지 세팅

`input.yaml` 내부 설정값을 변경하며 툴로 생성하려는 OpenSQL 패키지의 호환 OS 종류와 버전, OpenSQL 패키지 구성 컴포넌트 정보를 변경할 수 있습니다

```yaml
# available version은 현재 툴에서 지원되는 OS 및 OpenSQL 컴포넌트 버전을 기재
# (추후 필요에 따라 지원 버전 추가 예정)


# 생성하려는 OpenSQL 패키지의 설치호환 OS 종류 및 버전 설정
os:
  name: oraclelinux
  version: 8.10
# available version: {
#   oraclelinux: [ 8.0 ~ 8.10, 9 ]
#   rockylinux: [ 8.4 ~ 8.10, 9.0 ~ 9.4 ]
# }

# OpenSQL 설치 패키지에 포함된 PostgreSQL 버전 정보
database:
  name: postgresql
  version: 15.8
# available version: [ 15.8 ]

# OpenSQL 설치 패키지에 포함시킬 컴포넌트(third party 툴, 유틸, pg extension) 설정
# 주석처리시 해당 컴포넌트는 OpenSQL 패키지에서 배제 가능
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

    # pg extension들을 설치하는데 필요한 유틸(make, llvm)의 rpm 패키지
  - name: pg_build_extension_install_utils
    version: 1.0.0
    # available version: [ 1.0.0 ]

  - name: pg_hint_plan
    version: 1.5.2
    # available version: [ 1.5.2 ]

  - name: pgaudit
    version: 1.7.0
    # available version: [ 1.7.0 ]

  - name: credcheck
    version: 2.8.0
    # available version: [ 2.8.0 ]

  - name: system_stats
    version: 3.2
    # available version: [ 3.2 ]
```


### 패키지 생성 실행

`input.yaml` 설정 후, 터미널을 통해 아래 파이썬 명령 수행으로 OpenSQL 패키지를 생성합니다

```
python3 package.py
```

(패키지 생성은 하드웨어 성능에 따라 다르나 대략 5분 정도 소요)  

## 생성된 OpenSQL 설치 패키지

- 스크립트 `package.py`가 위치한 곳에 `opensql.tar` 파일 생성됩니다

- `tar -xvf opensql.tar` 커맨드로 tar 압축해제 시, `opensql` 디렉토리가 생성되고, 해당 디렉토리 내부에 설치파일들이 컴포넌트 디렉토리 별로 분류되어 제공됩니다

### 패키지 구성요소

`opensql` 디렉토리
  * `METADATA` 현재 opensql.tar 패키지에 포함된 컴포넌트의 버전 정보를 기술한 메타데이터
  * `postgresql` rpm 디렉토리
  * `pgpool` rpm 디렉토리
  * `postgis` rpm 디렉토리
  * `barman` rpm 디렉토리
  * `extension-utils-make` `make` rpm 디렉토리 (pg extension 설치 유틸)
  * `extension-utils-llvm` `llvm` rpm 디렉토리 (pg extension 설치 유틸)
  * `pg_hint_plan` rpm 디렉토리 (pg extension)
  * `pgaudit` make install 디렉토리 (pg extension)
  * `system_stats` make install 디렉토리 (pg extension)
  * `credcheck` make install 디렉토리 (pg extension)

`METADATA`

이 opensql.tar를 설치 가능한 OS 버전이 무엇인지, 또 설치가능한 컴포넌트들이 어떤 버전으로 해당 opensql.tar에 포함되어 있는지 기술한 명세서 입니다.

내용 예시는 아래와 같습니다

```bash
[root@1707c7ea4ee0 opensql]# cat METADATA 

# oraclelinux 8.10에서 아래 패키지들이 설치 가능함을 나타냅니다
[SUPPORTED OS VERSION]
oraclelinux 8.10

# 현재 tar에 포함되어 있는 설치 가능한 컴포넌트들 목록입니다.
[INSTALLABLE BINARIES]
postgresql 15.8
pgpool 4.4.4
postgis 3.4.0
barman 3.11.1
pg_build_extension_install_utils 1.0.0
pg_hint_plan 1.5.2
pgaudit 1.7
credcheck 2.8.0
system_stats 3.2

[root@1707c7ea4ee0 opensql]#
```

### 컴포넌트 설치

<!-- OpenSQL 설치 패키지에 포함된 컴포넌트들은  다음과 같은 설치 타입으로 나뉩니다

- `rpm` rpm 파일 형태로 제공 (Redhat 계열 OS 지원)
- `make install` 미리 빌드한 C 바이너리 형태로 제공 -->

#### rpm 설치 (Oraclelinux, Rockylinux)

- redhat 계열 os에 기본 탑재된 `rpm` 명령어를 이용하여 디렉토리 내부에 rpm 파일로 제공되는 컴포넌트들을 설치합니다.  

- `opensql` 디렉토리를 기준으로, 다음과 같이 rpm파일을 설치합니다.

* OpenSQL 패키지 내부 모든 rpm 파일 컴포넌트들 설치

  `rpm -Uvh --nodeps --replacepkgs --replacefiles ./**/*.rpm`

* 컴포넌트 개별 선택 설치

  `rpm -Uvh --nodeps --replacepkgs --replacefiles ./{컴포넌트 디렉토리 이름}/*.rpm`

  ex) 컴포넌트 중 postgresql만 설치할때,

  `rpm -Uvh --nodeps --replacepkgs --replacefiles ./postgresql/*.rpm`


**(단, 위 명령어들은 머신에 이미 동일한 rpm 패키지가 설치되어 있으면 교체를 진행하고, rpm 패키지 구성 내용 중 동일한 파일이 존재하면 교체를 진행하면서 rpm 설치를 진행하므로 유의가 필요합니다.)**


>_(참고) rpm 명령어 구조_  
>_`rpm {설치옵션} [부가옵션] {설치하려는 rpm 파일의 경로}`_
>* 설치 옵션  
>    * 신규 설치 `-ivh` : rpm이 이미 설치가 되어 있으면 설치 안함
>    * 업그레이드 `-Uvh` : rpm이 이미 설치 되어 있으면 더 최신 버전일 경우 설치 진행
>* 부가 옵션
>    * `--nodeps` : rpm 설치 시 기본적으로 의존성 rpm 유무 체크하고 없으면 설치 중단하는데, 이 옵션 추가 시 의존성 체크를 하지 않고 rpm 설치 진행하도록 함
>    * `--replacepkgs` : 이미 동일한 버전의 패키지가 설치되어 있으면 rpm 설치를 거부하는데, 이 옵션 추가 시 rpm 패키지를 교체하면서 설치 진행하도록 함
>    * `--replacefiles` : 이미 설치된 패키지의 구성 파일과 겹치는 구성 파일이 있으면 rpm 설치를 거부하는데, 이 옵션 추가 시 구성파일을 교체하면서 설치 진행하도록 함

#### make install 설치 (pre-built pg extension C binaries)

- 미리 빌드한 C 바이너리 형태로 제공되는 pg extension 파일들을 설치합니다

- 디렉토리 내부 `Makefile` 파일이 있는 pg extension 컴포넌트들에 대해,  
  설치하고자 컴포넌트의 디렉토리 이동 후 `make install`로 설치합니다

- 기본 구조는 `make install` 동일하나, pg extension 별로 추가로 넘겨줘야 하는 인자 값이 있을 수 있습니다

- 현재 제공되는 pg extension들의 `make install` 전체 커맨드는 다음과 같습니다

  - pgaudit: `make install USE_PGXS=1 PG_CONFIG=/usr/pgsql-{PG 메이저 버전}/bin/pg_config`
  - system_stats: `make install USE_PGXS=1`
  - credcheck: `make install`  
  

**make install 설치 주의사항**
- 설치하려는 서버 환경에서 postgresql의 바이너리 파일들 경로가 **PATH 환경변수($PATH)** 에 등록이 되어 있어야 합니다 (터미널에서 `pg_config` 사용이 가능해야 합니다) 

- extension들의 디렉토리 내부에 `install` 이라는 description 파일이 존재합니다.  
  해당 파일을 통해 `make install` 수행 시 필요한 인자 값을 확인할 수 있습니다

- `make install`은 사전에 `make`, `llvm` 유틸이 설치되어 있어야 수행 가능합니다.   
  (`extension-utils-make`, `extension-utils-llvm` 디렉토리는 해당 유틸들의 rpm 파일을 제공하므로, 필요시 설치 하시면 됩니다)


## 기타

opensql.tar 패키지는 OpenSQL 컴포넌트를 설치하는 작업만 포함되었으므로, 각 구성요소의 설치가 완료되면 해당 컴포넌트의 설정(postgresql init, pgpool backend conf 설정 등..)은 직접 진행해주셔야 합니다.