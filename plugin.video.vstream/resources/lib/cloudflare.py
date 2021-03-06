#-*- coding: utf-8 -*-
# https://github.com/Kodi-vStream/venom-xbmc-addons
#
#alors la j'ai pas le courage
from __future__ import division

import re,os
import urllib2,urllib
import xbmc
import xbmcaddon

#---------------------------------------------------------
#Gros probleme, mais qui a l'air de passer
#Le headers "Cookie" apparait 2 fois, il faudrait lire la precedente valeur
#la supprimer et remettre la nouvelle avec les 2 cookies
#Non conforme au protocole, mais ca marche (pour le moment)
#-----------------------------------------------------------

#Cookie path
#C:\Users\BRIX\AppData\Roaming\Kodi\userdata\addon_data\plugin.video.vstream\

#Light method
#Ne marche que si meme user-agent
    # req = urllib2.Request(sUrl,None,headers)
    # try:
        # response = urllib2.urlopen(req)
        # sHtmlContent = response.read()
        # response.close()

    # except urllib2.HTTPError, e:

        # if e.code == 503:
            # if CloudflareBypass().check(e.headers):
                # cookies = e.headers['Set-Cookie']
                # cookies = cookies.split(';')[0]
                # sHtmlContent = CloudflareBypass().GetHtml(sUrl,e.read(),cookies)

#Heavy method
# sHtmlContent = CloudflareBypass().GetHtml(sUrl)

PathCache = xbmc.translatePath(xbmcaddon.Addon('plugin.video.vstream').getAddonInfo("profile"))
UA = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; de-DE; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'

def parseIntOld(chain):

    chain = chain.replace(' ','')
    chain = re.sub(r'!!\[\]','1',chain) # !![] = 1
    chain = re.sub(r'\(!\+\[\]','(1',chain)  #si le bloc commence par !+[] >> +1
    chain = re.sub(r'(\([^()]+)\+\[\]\)','(\\1)*10)',chain)  # si le bloc fini par +[] >> *10

    #bidouilles a optimiser non geree encore par regex
    chain = re.sub(r'\(\+\[\]\)','0',chain)
    if chain.startswith('!+[]'):
        chain = chain.replace('!+[]','1')

    return eval(chain)

def checkpart(s,sens):
    number = 0
    p = 0
    if sens == 1:
        pos = 0
    else:
        pos = len(s) - 1

    try:
        while (1):
            c = s[pos]
            
            if ((c == '(') and (sens == 1)) or ((c == ')') and (sens == -1)):
                p = p + 1
            if ((c == ')') and (sens == 1)) or ((c == '(') and (sens == -1)):
                p = p - 1
            if (c == '+') and (p == 0) and (number > 1):
                break
                
            number +=1
            pos=pos + sens
    except:

        pass

        
    if sens == 1:
        return s[:number],number
    else:
        return s[-number:],number

def parseInt(s):

    offset=1 if s[0]=='+' else 0
    chain = s.replace('!+[]','1').replace('!![]','1').replace('[]','0').replace('(','str(')[offset:]
    
    if '/' in chain:
        
        #print('division ok ')
        #print('avant ' + chain)
        
        val = chain.split('/')
        gauche,sizeg = checkpart(val[0],-1)
        droite,sized = checkpart(val[1],1)
        sign = ''

        chain = droite.replace(droite,'')

        if droite.startswith('+') or droite.startswith('-'):
            sign = droite[0]
            droite = droite[1:]
        
        #print('debug1 ' + str(gauche))
        #print('debug2 ' + str(droite))
        
        gg = eval(gauche)
        dd = eval(droite)
        
        chain = val[0][:-sizeg] + str(gg) + '/' + str(dd) + val[1][sized:]

        #print('apres ' + chain)

    val = float( eval(chain))

    return val


def CheckIfActive(data):
    if 'Checking your browser before accessing' in data:
    #if ( "URL=/cdn-cgi/" in head.get("Refresh", "") and head.get("Server", "") == "cloudflare-nginx" ):
        return True
    return False

def showInfo(sTitle, sDescription, iSeconds=0):
    if (iSeconds == 0):
        iSeconds = 1000
    else:
        iSeconds = iSeconds * 1000
    xbmc.executebuiltin("Notification(%s,%s,%s)" % (str(sTitle), (str(sDescription)), iSeconds))

class NoRedirection(urllib2.HTTPErrorProcessor):
    def http_response(self, request, response):
        return response

class CloudflareBypass(object):

    def __init__(self):
        self.state = False
        self.HttpReponse = None
        self.Memorised_Headers = None

    def DeleteCookie(self,Domain):
        xbmc.log('Effacement cookies')
        file = os.path.join(PathCache,'Cookie_'+ str(Domain) +'.txt')
        os.remove(os.path.join(PathCache,file).decode("utf-8"))

    def SaveCookie(self,Domain,data):
        Name = os.path.join(PathCache,'Cookie_'+ str(Domain) +'.txt').decode("utf-8")

        #save it
        file = open(Name,'w')
        file.write(data)

        file.close()

    def Readcookie(self,Domain):
        Name = os.path.join(PathCache,'Cookie_'+ str(Domain) +'.txt').decode("utf-8")

        try:
            file = open(Name,'r')
            data = file.read()
            file.close()
        except:
            return ''

        return data

    #Return param for head
    def GetHeadercookie(self,url):
        #urllib.quote_plus()
        Domain = re.sub(r'https*:\/\/([^/]+)(\/*.*)','\\1',url)
        cook = self.Readcookie(Domain.replace('.','_'))
        if cook == '':
            return ''

        return '|' + urllib.urlencode({'User-Agent':UA,'Cookie': cook })

    def SetHeader(self):
        head=[]
        if not (self.Memorised_Headers):
            head.append(('User-Agent', UA))
            head.append(('Host' , self.host))
            head.append(('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'))
            head.append(('Referer', self.url))
            head.append(('Content-Type', 'text/html; charset=utf-8'))
        else:
            for i in self.Memorised_Headers:
                if ('Content-Type' not in i) and ('Accept-charset' not in i):
                    head.append((i,self.Memorised_Headers[i]))
        return head

    def GetResponse(self,htmlcontent):
        
        line1 = re.findall('var s,t,o,p,b,r,e,a,k,i,n,g,f, (.+?)={"(.+?)":\+*(.+?)};',htmlcontent)

        varname = line1[0][0] + '.' + line1[0][1]
        calcul = parseInt(line1[0][2])

        AllLines = re.findall(';' + varname + '([*\-+])=([^;]+)',htmlcontent)
        
        #print(">>>>>>>>>>>>>>>>: " + format(calcul,'.17g'))

        for aEntry in AllLines:
            calcul = eval( format(calcul,'.17g') + str(aEntry[0]) + format(parseInt(aEntry[1]),'.17g'))
            #print(">>>>>>>>>>>>>>>>: " + format(calcul,'.17g')+ '\n')

        rep = calcul + len(self.host)

        return format(rep,'.10f')

    def GetReponseInfo(self):
        return self.HttpReponse.geturl(), self.HttpReponse.info()

    def GetHtml(self,url,htmlcontent = '',cookies = '',postdata = '',Gived_headers = ''):
    
        #Memorise headers
        self.Memorised_Headers = Gived_headers

        #For debug
        if (False):
            xbmc.log('Headers present ' + str(Gived_headers), xbmc.LOGNOTICE)
            xbmc.log('url ' + url, xbmc.LOGNOTICE)
            if (htmlcontent):
                xbmc.log('code html ok', xbmc.LOGNOTICE)
            xbmc.log('cookies passés' + cookies, xbmc.LOGNOTICE)

        self.hostComplet = re.sub(r'(https*:\/\/[^/]+)(\/*.*)','\\1',url)
        self.host = re.sub(r'https*:\/\/','',self.hostComplet)

        self.url = url

        cookieMem = self.Readcookie(self.host.replace('.','_'))
        if not (cookieMem == ''):

            cookies = cookieMem
            xbmc.log('cookies present sur disque', xbmc.LOGNOTICE)

            #Redirection possible
            opener = urllib2.build_opener()
            opener.addheaders = self.SetHeader()

            #Add saved cookies
            opener.addheaders.append (('Cookie', cookies))

            try:
                self.HttpReponse = opener.open(url,postdata)
                htmlcontent = self.HttpReponse.read()
                head = self.HttpReponse.headers
                self.HttpReponse.close()
                
            except urllib2.HTTPError, e:
                if e.code == 503:
                    htmlcontent = e.read()
                    head = e.headers
                    
            if not CheckIfActive(htmlcontent):
                # ok no more protection
                return htmlcontent

            #Arf, problem, cookies not working, delete them
            xbmc.log('Cookies Out of date', xbmc.LOGNOTICE)
            self.DeleteCookie(self.host.replace('.','_'))

            #Get the first new cookie, we already have the new html code
            cookies = ''
            if 'Set-Cookie' in head:
                cookies = head['Set-Cookie']
                cookies = cookies.split(';')[0]

        #if we need a first load
        if (htmlcontent == '') or (cookies == ''):

            opener = urllib2.build_opener(NoRedirection)
            opener.addheaders = self.SetHeader()

            self.HttpReponse = opener.open(url,postdata)

            #code
            htmlcontent = self.HttpReponse.read()

            #fh = open('c:\\test.txt', "r")
            #htmlcontent = fh.read()
            #fh.close()

            #if no protection
            head = self.HttpReponse.headers
            if not CheckIfActive(htmlcontent):
                return htmlcontent

            xbmc.log("Page protegée, tout a charger", xbmc.LOGNOTICE)
            #cookie
            head = self.HttpReponse.headers
            if 'Set-Cookie' in head:
                cookies = head['Set-Cookie']
                cookies = cookies.split(';')[0]

            self.HttpReponse.close()
            
        #fh = open('c:\\test.txt', "w")
        #fh.write(htmlcontent)
        #fh.close()

        #2 eme etape recuperation parametres
        hash = re.findall('<input type="hidden" name="jschl_vc" value="(.+?)"\/>',htmlcontent)[0]
        passe = re.findall('<input type="hidden" name="pass" value="(.+?)"\/>',htmlcontent)[0]

        #calcul de la reponse
        rep = self.GetResponse(htmlcontent)

        #Temporisation
        #j'en peux plus de cette popup xD
        #showInfo("Information", 'Decodage protection CloudFlare' , 5)
        xbmc.sleep(5000)

        NewUrl = self.hostComplet + '/cdn-cgi/l/chk_jschl?jschl_vc='+ urllib.quote_plus(hash) +'&pass=' + urllib.quote_plus(passe) + '&jschl_answer=' + rep

        opener = urllib2.build_opener(NoRedirection)
        opener.addheaders = self.SetHeader()

        #Add first cookie
        if not cookies == '':
            opener.addheaders.append(('Cookie', cookies))
        
        #Rajout headers manquants
        if 'Referer' not in opener.addheaders:
            opener.addheaders.append(('Referer', self.url))
        if 'Accept' not in opener.addheaders:
            opener.addheaders.append(('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'))

        self.HttpReponse = opener.open(NewUrl,postdata)
        
        #xbmc.log("Headers send " + str(opener.addheaders), xbmc.LOGNOTICE)
        #xbmc.log("cookie send " + str(cookies), xbmc.LOGNOTICE)
        #xbmc.log("header recu " + str(self.HttpReponse.headers), xbmc.LOGNOTICE)
        #xbmc.log("Url " + str(NewUrl), xbmc.LOGNOTICE)

        if 'Set-Cookie' in self.HttpReponse.headers:
            cookies2 = str(self.HttpReponse.headers.get('Set-Cookie'))
            c1 = re.findall('__cfduid=(.+?);',cookies2)
            c2 = re.findall('cf_clearance=(.+?);',cookies2)

            #If we have only cf_clearance, it's still ok, it s the more important
            if c2 and not c1:
                c1 = re.findall('__cfduid=([0-9a-z]+)',cookies)

            if not c1 or not c2:
                xbmc.log("Probleme protection Cloudflare : Decodage rate", xbmc.LOGNOTICE)
                showInfo("Erreur", 'Probleme protection CloudFlare' , 5)
                self.HttpReponse.close()
                return ''

            cookies = '__cfduid=' + c1[0] + '; cf_clearance=' + c2[0]
        elif 'Please complete the security check' in self.HttpReponse.read():
            #fh = open('c:\\test.txt', "w")
            #fh.write(self.HttpReponse.read())
            #fh.close()
            xbmc.log("Probleme protection Cloudflare : Protection captcha", xbmc.LOGNOTICE)
            showInfo("Erreur", 'Probleme CloudFlare, pls Retry' , 5)
            self.HttpReponse.close()
            return ''           
        else:
            xbmc.log("Probleme protection Cloudflare : Cookies manquants", xbmc.LOGNOTICE)
            showInfo("Erreur", 'Probleme protection CloudFlare' , 5)
            self.HttpReponse.close()
            return ''

        self.HttpReponse.close()

        #Memorisation
        self.SaveCookie(self.host.replace('.','_'),cookies)

        #3 eme etape : on refait la requete mais avec les nouveaux cookies
        opener = urllib2.build_opener()
        opener.addheaders = self.SetHeader()

        #Add the two cookies
        opener.addheaders.append (('Cookie', cookies))

        self.HttpReponse = opener.open(url,postdata)
        htmlcontent = self.HttpReponse.read()
        head = self.HttpReponse.headers
        if CheckIfActive(htmlcontent):
            #Arf new cookie not working
            xbmc.log("New cookie not working", xbmc.LOGNOTICE)
            #self.DeleteCookie(self.host.replace('.','_'))
            self.HttpReponse.close()
            return ''

        self.HttpReponse.close()

        return htmlcontent
