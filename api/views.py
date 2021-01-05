from django.shortcuts import render, redirect
from api.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from radar import settings
from django.core.cache import cache
import uuid, re, pytz
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import APIException
from django.db.models import Q
import datetime
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework.decorators import api_view, throttle_classes
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

def validate_fields(codigo,data, hora):
    try:
        val = int(codigo)
    except ValueError:
        raise APIException('Erro de validação: Código')
    try:
        dt=datetime.datetime(*[int(item) for item in data.split('-')])
    except ValueError:
        raise APIException("Erro de validação: Data")
    except TypeError:
        raise APIException("Erro de validação: Data")
    try:
        h = int(hora)
    except ValueError:
        raise APIException('Erro de validação: Hora')
    if h<0 or h>23:
        raise APIException('Erro de validação: Hora')
    
    radar=Radar.objects.filter(codigo__contains=codigo)
    if len(radar)==0:
        raise APIException("Erro de validação: Código não existe")

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def map(request):
    if not request.user.is_authenticated:
        return redirect('%s?next=%s' % ('/login/', request.path))
    try:
        token=Token.objects.get(user=request.user)
    except Token.DoesNotExist:
        token=Token(user=request.user)
        token.save()
    
    return render(request, 'map.html', {
        "hostname":"%s://%s/" % (settings.PROTOCOL, settings.HOSTNAME),
        "user": request.user,
        "token": token.key,
    })

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def renew(request):
    if not request.user.is_authenticated:
        return redirect('%s?next=%s' % ('/login/', request.path))
    try:
        token=Token.objects.get(user=request.user)
        token.delete()
    except Token.DoesNotExist:
        pass
    token=Token(user=request.user)
    token.save()
    return JsonResponse({"mess": "Token criado", "status":"200", "token":token.key})

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def get_datas(request):
    if 'clear' in request.GET:
        cache.delete('datas')
    results=cache.get('datas')
    if results is None:
        du=datetime.date(2010,1,1)
        today=datetime.date.today()
        results=[]
        from django.db import connection
        while du<today:
            du+=datetime.timedelta(days=1)
            with connection.cursor() as c:
                c.execute("select localidade from contagens where timezone('GMT-3'::text, data_e_hora)::date=%s limit 1", (du.strftime('%Y-%m-%d'),))
                ru=c.fetchone()
                if ru is not None:
                    results.append("%s/%s/%s" % (str(du.day).rjust(2,'0'), str(du.month).rjust(2,'0'), str(du.year).rjust(4,'0')))
        cache.set('datas', results)
    return JsonResponse({
        "results":results
    })

def get_local(codigo):
    from django.db import connection
    with connection.cursor() as c:
        c.execute("select  st_x(geom), st_y(geom),codigo from base_radares where position(%s in codigo) > 0;",
                (str(codigo),))
        return c.fetchone()

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def get_locais_por_data(request, d):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    r = Radar.objects.filter(data_publicacao__lte=d)
    j=[ {"x":radar.geom.x,"y":radar.geom.y, "lote":radar.lote, "id":radar.id, "codigo":re.split("\s*-\s*", radar.codigo)} for radar in r ]
    return JsonResponse(j, safe=False)
    
@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def get_locais(request):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    r = Radar.objects.all()
    j=[ {"x":radar.geom.x,"y":radar.geom.y, "lote":radar.lote, "id":radar.id, "codigo":re.split("\s*-\s*", radar.codigo)} for radar in r ]
    return JsonResponse(j, safe=False)

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def get_viagens(request, codigo, data):
    return get_viagens_hora(request._request,codigo,data,"8")

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def get_viagens_hora(request, codigo, data, hora):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    validate_fields(codigo, data, hora)
    dt=datetime.datetime(*[int(item) for item in data.split('-')]+[int(hora), 0, 0, 0, pytz.timezone('UTC')])
    radar=Radar.objects.filter(codigo__contains=codigo)
    if len(radar)==0:
        raise APIException("Erro de validação: Código não existe")
    ds=dt+datetime.timedelta(hours=1)
    query=Q(origem=codigo)
    query.add(Q(data_inicio__gt=dt), Q.AND)
    query.add(Q(data_inicio__lte=ds), Q.AND)
    other=Q(destino=codigo)
    other.add(Q(data_final__gt=dt), Q.AND)
    other.add(Q(data_final__lte=ds), Q.AND)
    query.add(other, Q.OR)
    trips=Trajeto.objects.filter(query)
    viagens={}
    res=[]
    for v in trips:
        if not v.viagem_id in viagens:
            viagens[v.viagem_id]=v.viagem
            viagens[v.viagem_id].data_inicio=v.data_inicio
            viagens[v.viagem_id].data_final=v.data_final
        else:
            if v.data_inicio < viagens[v.viagem_id].data_inicio:
                viagens[v.viagem_id].data_inicio=v.data_inicio
            if v.data_final > viagens[v.viagem_id].data_final:
                viagens[v.viagem_id].data_final=v.data_final
            
    res=[{"id":viagens[c].id, "data_inicio":viagens[c].data_inicio, "data_final":viagens[c].data_final} for c in viagens.keys()]
    return JsonResponse({"result":res, "total":len(res)})

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def get_trajetos_por_viagem(request, viagem_id):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    try:
        val = int(viagem_id)
    except ValueError:
        raise APIException('Erro de validação: viagem_id')
    trips=Trajeto.objects.filter(viagem_id=viagem_id)
    res=[]
    for v in trips:
        r=Route.objects.filter(origem=v.origem, destino=v.destino)
        dist=None
        vm=None
        if len(r)>0:
            dist=r[0].dist
        if dist is not None:
            t=(v.data_final-v.data_inicio).total_seconds()
            if t > 0:
                vm=round(float(dist)/float(t)*3.6)
        res.append({"id":v.id, "inicio":v.origem, "final":v.destino, "data_inicio":v.data_inicio, "data_final":v.data_final, "velocidade_media":vm, "distancia":dist})
    return JsonResponse({"result":res, "total":len(res)})

def roteirize(p,q):
    if p==q:
        print("Nothing to do, start equals end")
        return None
    origem = reverse_geocode(p[0],p[1])
    destino=reverse_geocode(q[0],q[1])
    if origem is None or destino is None:
        return None
    from django.db import connection
    with connection.cursor() as c:
        c.execute(
            "select m, st_astext(m) from ("
            "select st_linemerge(st_union(st_union(st_geomfromwkb(%s::geometry), dg),st_geomfromwkb(%s::geometry))) as m from ("
            "select case when st_geometrytype(g)='ST_MultiLineString' then st_geometryn(g, 1) else g end as dg from (select st_linemerge(st_union(s.geom)) as g from "
            "(select seq,path_seq,node,edge,cost,agg_cost from pgr_dijkstra('SELECT gid as id,source, target, st_length(geom) as cost, st_length(geom) as reverse_cost FROM segmento_viario', %s,%s))"
            " a left join segmento_viario s on s.id=a.edge) e"
            ") f"
            ") o",
            (origem[3],destino[3],origem[1], destino[2],)
        )


        res = c.fetchone()
        print(res[0])
        print(res[1])
        print("SRID=4326;POINT(%s %s)" % (p[0], p[1],))
        print("SRID=4326;POINT(%s %s)" % (q[0], q[1],))
        try:
            c.execute("select st_linelocatepoint(st_geomfromwkb(%s::geometry),st_transform(st_geomfromewkt(%s), 31983)) as ini, st_linelocatepoint(st_geomfromwkb(%s::geometry),st_transform(st_geomfromewkt(%s), 31983)) as fim",
                    (res[0], "SRID=4326;POINT(%s %s)" % (p[0], p[1],),res[0],"SRID=4326;POINT(%s %s)" % (q[0],q[1],)),
                    )
        except:
            c.execute(
                "select m, st_astext(m) from ("
                "select st_linemerge(dg) as m from ("
                "select case when st_geometrytype(g)='ST_MultiLineString' then st_geometryn(g, 1) else g end as dg from (select st_linemerge(st_union(s.geom)) as g from "
                "(select seq,path_seq,node,edge,cost,agg_cost from pgr_dijkstra('SELECT gid as id,source, target, st_length(geom) as cost, st_length(geom) as reverse_cost FROM segmento_viario', %s,%s))"
                " a left join segmento_viario s on s.id=a.edge) e"
                ") f"
                ") o",
                (origem[1], destino[2],)
            )
            res = c.fetchone()
            c.execute("select st_linelocatepoint(st_geomfromwkb(%s::geometry),st_transform(st_geomfromewkt(%s), 31983)) as ini, st_linelocatepoint(st_geomfromwkb(%s::geometry),st_transform(st_geomfromewkt(%s), 31983)) as fim",
                    (res[0], "SRID=4326;POINT(%s %s)" % (p[0], p[1],),res[0],"SRID=4326;POINT(%s %s)" % (q[0],q[1],)),
                    )
        ps=list(filter(lambda x: x is not None, list(c.fetchone())))
        print(ps)
        ps.sort()
        if len(ps)==0:
            print("Not found")
            return None
        else:
            c.execute("select g, st_geometrytype(g) from (\
                select g from (select st_linesubstring(st_geomfromwkb(%s::geometry)\
                        , %s, %s) as g) h\
                    )o", (res[0], ps[0], ps[1]))

            res=c.fetchone()
            if not res[1]=='ST_LineString':
                return None
            return res[0]

def reverse_geocode(x,y):
    from django.db import connection
    with connection.cursor() as c:
        c.execute(
            "select a.gid, a.source, a.target, a.linha from (select gid,source,target,st_linemerge(geom) as linha from segmento_viario order by geom <-> st_transform(ST_GeomFromEWKt(%s),31983) limit 1) as a",
            ("SRID=4326;POINT(%s %s)"%(x,y),)
        )
        return c.fetchone()

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def get_trajetos(request, codigo, data):
    return get_trajetos_hora(request._request, codigo, data, "8")

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def get_trajetos_hora(request, codigo, data, hora):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    v=validate_fields(codigo,data,hora)
    radar=Radar.objects.filter(codigo__contains=codigo)
    if len(radar)==0:
        raise APIException("Erro de validação: Código não existe")
    dt=datetime.datetime(*[int(item) for item in data.split('-')]+[int(hora), 0, 0, 0, pytz.timezone('UTC')])
    dt=dt.replace(hour=int(hora))
    ds=dt+datetime.timedelta(hours=1)
    query=Q(origem=codigo)
    query.add(Q(data_inicio__gt=dt), Q.AND)
    query.add(Q(data_inicio__lte=ds), Q.AND)
    other=Q(destino=codigo)
    other.add(Q(data_final__gt=dt), Q.AND)
    other.add(Q(data_final__lte=ds), Q.AND)
    query.add(other, Q.OR)
    trips=Trajeto.objects.filter(query)
    res=[]
    for v in trips:
        r=Route.objects.filter(origem=v.origem, destino=v.destino)
        dist=None
        vm=None
        if len(r)>0:
            dist=r[0].dist
        
        if (dist is None or r[0].geom is None) and 'recalculate' in request.GET:
            local_origem=get_local(v.origem)
            local_destino=get_local(v.destino)
            if local_origem is not None and local_destino  is not None:
                k=roteirize(local_origem, local_destino)
                print(k)
                if len(r)>0:
                    r[0].geom=k
                    r[0].save()
                else:
                    print("saving route")
                    rt=Route(origem=v.origem, destino=v.destino, geom=k)
                    rt.save()
                from django.db import connection
                with connection.cursor() as c:
                    c.execute("update route set dist=st_length(st_transform(geom, 32723)) where origem=%s and destino=%s" % (v.origem, v.destino))
                           
        if dist is not None:
            t=(v.data_final-v.data_inicio).total_seconds()
            if t > 0:
                vm=round(float(dist)/float(t)*3.6)
        res.append({"id":v.id, "inicio":v.origem, "final":v.destino, "data_inicio":v.data_inicio, "data_final":v.data_final, "velocidade_media":vm, "distancia":dist})
    return JsonResponse({"result":res, "total":len(res)})

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def get_distancia(request, a, b):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    try:
        val = int(a)
        val = int(b)
    except ValueError:
        raise APIException('Erro de validação: Código')
    rt=Route.objects.filter(origem=a,destino=b)
    if len(rt)>0:
        return JsonResponse({"dist":rt[0].dist, "origem":a, "destino":b, "geom":rt[0].geom.ewkt})
    local_origem=get_local(a)
    local_destino=get_local(b)
    if local_origem is not None and local_destino  is not None:
        k=roteirize(local_origem, local_destino)
        rt=Route(origem=a, destino=b, geom=k)
        rt.save()
        from django.db import connection
        with connection.cursor() as c:
            c.execute("update route set dist=st_length(st_transform(geom, 32723)) where origem=%s and destino=%s" % (a, b))
        rt.refresh_from_db()
        return JsonResponse({"dist":rt.dist, "origem":a, "destino":b, "geom":rt.geom.ewkt})
    else:
        return HttpResponse(status=400)                       


@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def get_velocidades(request, data, codigo):
    return get_velocidades_hora(request, data, "8", codigo)

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def get_velocidades_hora(request, data, hora, codigo):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    validate_fields(codigo,data,hora)
    radar=Radar.objects.filter(codigo__contains=codigo)
    if len(radar)==0:
        return HttpResponse(status=400)
    r=radar[0]
    dt=datetime.datetime(*[int(item) for item in data.split('-')])
    dt=dt.replace(hour=hora)
    ds=dt+datetime.timedelta(hours=1)

    spds=[]
    query=Q(origem=codigo)
    query.add(Q(data_inicio__gt=dt), Q.AND)
    query.add(Q(data_inicio__lte=ds), Q.AND)
    trips=Trajeto.objects.filter(query)
    for t in trips:
        spds.append({
            "velocidade":t.v0,
            "tipo":t.tipo,
            "data_e_hora":t.data_inicio
        })

    other=Q(destino=codigo)
    other.add(Q(data_final__gt=dt), Q.AND)
    other.add(Q(data_final__lte=ds), Q.AND)
    trips=Trajeto.objects.filter(query)
    for t in trips:
        spds.append({
            "velocidade":t.v1,
            "tipo":t.tipo,
            "data_e_hora":t.data_final
        })
    return JsonResponse({"result":spds, "total":len(spds)})
    

def get_detalhes(request, codigo):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    try:
        val = int(codigo)
    except ValueError:
        raise APIException('Erro de validação: Código')
    radar=Radar.objects.filter(codigo__contains=codigo)
    if len(radar)==0:
        return HttpResponse(status=400)
    r=radar[0]
    res={
        "codigo":r.codigo,
        "lote":r.lote,
        "endereco":r.endereco,
        "sentido":r.sentido,
        "referencia":r.referencia,
        "tipo_equip":r.tipo_equip,
        "enquadramento":r.enquadrame,
        "faixas":r.qtde_fxs_f,
        "velocidade":r.velocidade,
        "velocidade_cam_oni":r.velocidade_cam_oni,
        "velocidade_carro_moto":r.velocidade_carro_moto,
        "bairro":r.bairro,
        "data_publicacao":r.data_publicacao,
        "latitude":r.geom.y,
        "longitude":r.geom.x
    }
    return JsonResponse(res)

@api_view(['GET'])
@throttle_classes([UserRateThrottle])  
def get_contagens(request, data, codigo):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    validate_fields(codigo,data,"1")
    radar=Radar.objects.filter(codigo__contains=codigo)
    if len(radar)==0:
        return HttpResponse(status=400)
    r=radar[0]    
    dt=datetime.datetime(*[int(item) for item in data.split('-')])
    ds=dt+datetime.timedelta(days=1)
    contagens=Contagem.objects.filter(localidade=codigo,data_e_hora__gte=dt,data_e_hora__lt=ds)
    res=[{
        "codigo":c.localidade,
        "faixa":c.faixa,
        "tipo":c.tipo,
        "contagem":c.contagem,
        "autuacoes":c.autuacoes,
    #    "placas":c.placas,
        "data_e_hora":c.data_e_hora
    } for c in contagens]
    return JsonResponse({"result":res})

def api_login(request):
    if request.method=='GET':
        return render(request, 'login.html')
    else:
        username = request.POST['email']
        password = request.POST['senha']
        user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return redirect('/map/')
    else:
        return render(request, 'login.html', {"message":"Não foi possível fazer login com as credenciais fornecidas."})

def api_logout(request):
    logout(request)
    return redirect('/')

def signup(request):
    if request.method=='GET':
        return render(request, 'signup.html')
    else:
        if request.POST['senha']!=request.POST['confirmar_senha']:
            return JsonResponse({"mess": "Senhas diferem.", "status":"401"})
        u=User.objects.filter(email=request.POST['email'])
        if u.count():
            return JsonResponse({"mess": "Usuário já existe", "status":"401"})
        u=User(first_name=request.POST['name'], email=request.POST['email'], username=request.POST['email'], is_active=False)
        u.set_password(request.POST['senha'])

        u.save()
        token=str(uuid.uuid4())
        url="%s://%s/validate/%s/" % (settings.PROTOCOL,settings.HOSTNAME,token)
        cache.set("validator_%s" % (token,), u.id)
        
        msg = EmailMultiAlternatives(
            'API Dados de Radar - SMT',
            "Seu usuário foi criado. Acesse %s para validar seu cadastro."%(url), 
            settings.DEFAULT_FROM_EMAIL,
            [request.POST['email']],
        )
        html="Seu usuário foi criado. Clique <a href=\"%s\">aqui</a> para validar seu cadastro.<br>\
                Você também pode pode copiar a URL %s para seu navegador." % (url,url)
        msg.attach_alternative(html, "text/html")
        msg.send()
        return JsonResponse({"mess": "Usuário criado", "status":"200"})

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def validate(request, signup_token):
    uid=cache.get("validator_%s" % (signup_token,))
    if uid is None:
        mess="Token inválido ou expirado"
    else:
        u=User.objects.get(pk=uid)
        mess="Usuário validado: %s." % (u.username)
        u.is_active=True
        u.save()
        return render(request, 'validate.html', {'message':mess, 'username':u.username})
    return render(request, 'validate.html', {'message':mess, 'username':""})

@api_view(['GET'])
@throttle_classes([UserRateThrottle])
def reset_password(request, email):
    try:
        u=User.objects.get(email=email)
    except ObjectDoesNotExist as ex:
        raise Http404
    return JsonResponse({"mess": "Um link para alteração da senha foi enviado para %s" % email, "status":"200"})
