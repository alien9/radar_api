from django.shortcuts import render, redirect
from api.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from radar import settings
from django.core.cache import cache
import uuid, re
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import APIException
from django.db.models import Q
import datetime

def validate_fields(codigo,data):
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
    radar=Radar.objects.filter(codigo__contains=codigo)
    if len(radar)==0:
        raise APIException("Erro de validação: Código não existe")

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

def get_datas(request):
    c=Contagem.objects.distinct('data_e_hora')
    return JsonResponse({
        "results":list(set([d.data_e_hora.strftime('%d/%m/%Y') for d in c]))
    })

def get_locais_por_data(request, d):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    r = Radar.objects.filter(data_publicacao__lte=d)
    j=[ {"x":radar.geom.x,"y":radar.geom.y, "lote":radar.lote, "id":radar.id, "codigo":re.split("\s+-?\s+", radar.codigo)} for radar in r ]
    return JsonResponse(j, safe=False)

def get_locais(request):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    r = Radar.objects.all()
    j=[ {"x":radar.geom.x,"y":radar.geom.y, "lote":radar.lote, "id":radar.id, "codigo":re.split("\s+-?\s+", radar.codigo)} for radar in r ]
    return JsonResponse(j, safe=False)

def get_viagens(request, codigo, data):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    validate_fields(codigo, data)
    dt=datetime.datetime(*[int(item) for item in data.split('-')])
    radar=Radar.objects.filter(codigo__contains=codigo)
    if len(radar)==0:
        raise APIException("Erro de validação: Código não existe")
    ds=dt+datetime.timedelta(days=1)
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
    res=[{"id":viagens[c].id, "data_inicio":viagens[c].data_inicio, "data_final":viagens[c].data_final} for c in viagens.keys()]
    return JsonResponse({"result":res, "total":len(res)})

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
        res.append({"id":v.id, "inicio":v.origem, "final":v.destino, "data_inicio":v.data_inicio, "data_final":v.data_final, "velocidade_media":vm})
    return JsonResponse({"result":res, "total":len(res)})

def get_trajetos(request, codigo, data):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    v=validate_fields(codigo,data)
    dt=datetime.datetime(*[int(item) for item in data.split('-')])
    radar=Radar.objects.filter(codigo__contains=codigo)
    if len(radar)==0:
        raise APIException("Erro de validação: Código não existe")
    dt=datetime.datetime(*[int(item) for item in data.split('-')])
    ds=dt+datetime.timedelta(days=1)
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
        if dist is not None:
            t=(v.data_final-v.data_inicio).total_seconds()
            if t > 0:
                vm=round(float(dist)/float(t)*3.6)
        res.append({"id":v.id, "inicio":v.origem, "final":v.destino, "data_inicio":v.data_inicio, "data_final":v.data_final, "velocidade_media":vm})
    return JsonResponse({"result":res, "total":len(res)})

def get_velocidades(request, data, codigo):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    validate_fields(codigo,data)
    radar=Radar.objects.filter(codigo__contains=codigo)
    if len(radar)==0:
        return HttpResponse(status=400)
    r=radar[0]
    dt=datetime.datetime(*[int(item) for item in data.split('-')])
    ds=dt+datetime.timedelta(days=1)

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
  
def get_contagens(request, data, codigo):
    if not request.user.is_authenticated:
        user=TokenAuthentication().authenticate(request)
        if user is None:
            return HttpResponse(status=401)
    validate_fields(codigo,data)
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
        u=User(email=request.POST['email'], username=request.POST['email'], is_active=False)
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