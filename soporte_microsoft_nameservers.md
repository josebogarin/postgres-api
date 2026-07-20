# Solicitud de soporte - Cambio de servidores de nombres (Nameservers) del dominio lambdapy.org

Estimado equipo de soporte de Microsoft,

Me dirijo a ustedes para solicitar asistencia con el cambio de los servidores de nombres (nameservers) de mi dominio **lambdapy.org**, actualmente gestionado a través de Microsoft 365.

## Situación actual

El dominio lambdapy.org está registrado y administrado bajo mi suscripción de Microsoft 365. Los nameservers actuales son:

- ns1.bdm.microsoftonline.com
- ns2.bdm.microsoftonline.com
- ns3.bdm.microsoftonline.com
- ns4.bdm.microsoftonline.com

## Cambio solicitado

Necesito transferir la gestión del DNS a Cloudflare para configurar un túnel seguro (Cloudflare Tunnel) que permita exponer una aplicación web propia de forma segura. Los nuevos nameservers a configurar son:

- **delilah.ns.cloudflare.com**
- **watson.ns.cloudflare.com**

## Aclaración importante

Entiendo que al realizar este cambio, los registros DNS actuales de Microsoft 365 (Exchange Online, Teams/Lync, Intune) dejarán de ser gestionados por Microsoft. Ya realicé la importación de todos los registros existentes en Cloudflare antes de solicitar este cambio, por lo que los servicios de correo y colaboración (Outlook, Teams) continuarán funcionando sin interrupción.

Los registros importados en Cloudflare incluyen:

- MX: lambdapy-org.mail.protection.outlook.com (Exchange Online)
- TXT: v=spf1 include:spf.protection.outlook.com -all (SPF)
- CNAME: autodiscover, lyncdiscover, sip (Teams/Lync)
- SRV: _sip._tls, _sipfederationtls._tcp (Teams)
- CNAME: enterpriseenrollment, enterpriseregistration (Intune)

## Solicitud

Por favor indíquenme los pasos o realicen el cambio necesario para que los nameservers del dominio lambdapy.org apunten a Cloudflare. Si el dominio fue adquirido a través de un registrador asociado (como GoDaddy), agradezco me indiquen cómo acceder a esa cuenta para realizar el cambio yo mismo.

Quedo a disposición para cualquier información adicional.

Saludos cordiales,
Jose Bogarin
jose.bogarin@gmail.com
