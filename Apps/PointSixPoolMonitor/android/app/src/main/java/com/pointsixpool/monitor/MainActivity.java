package com.pointsixpool.monitor;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.view.View;
import android.view.WindowInsets;
import android.widget.*;
import org.json.*;
import javax.net.ssl.HttpsURLConnection;
import java.io.*;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

/** Native read-only wallet monitoring. Account writes retain website MFA/CSRF checks. */
public final class MainActivity extends Activity {
 private final ExecutorService io=Executors.newSingleThreadExecutor();
 private final Handler handler=new Handler(Looper.getMainLooper());
 private LinearLayout root,content; private EditText wallet;
 private String tab="Income",status="Add your public ZEC wallet.";
 private JSONArray workers=new JSONArray(); private Double credit=null,price=null;
 private boolean busy=false,foreground=false,workFresh=false;
 private final Runnable refreshTick=new Runnable(){public void run(){if(foreground){refresh();handler.postDelayed(this,30000);}}};
 private TextView text(String value,int size){TextView v=new TextView(this);v.setText(value);v.setTextSize(size);v.setTextColor(Color.rgb(231,237,242));v.setPadding(0,8,0,8);return v;}
 private Button button(String value,Runnable action){Button v=new Button(this);v.setText(value);v.setAllCaps(false);v.setOnClickListener(x->action.run());return v;}
 @Override public void onCreate(Bundle saved){super.onCreate(saved);root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(16,16,16,16);root.setBackgroundColor(Color.rgb(16,24,32));
 root.setOnApplyWindowInsetsListener((v,insets)->{if(android.os.Build.VERSION.SDK_INT>=30){android.graphics.Insets i=insets.getInsets(WindowInsets.Type.systemBars());v.setPadding(16,16+i.top,16,16+i.bottom);}return insets;});
 root.addView(text("PointSixPool Monitor",23));wallet=new EditText(this);wallet.setTextColor(Color.WHITE);wallet.setSingleLine(true);wallet.setHintTextColor(Color.GRAY);wallet.setHint("Public ZEC t1/t3 address");wallet.setInputType(android.text.InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD);wallet.setText(getPreferences(0).getString("publicWallet",""));root.addView(wallet);
 LinearLayout nav=new LinearLayout(this);for(String name:new String[]{"Income","Workers","Account"})nav.addView(button(name,()->{if("Account".equals(name)){try{startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse("https://pointsixpool.com/mobile/")));}catch(android.content.ActivityNotFoundException missing){Toast.makeText(this,"Install or enable a web browser for account sign-in.",Toast.LENGTH_LONG).show();}}else{tab=name;render();}}),new LinearLayout.LayoutParams(0,48,1));root.addView(nav);
 ScrollView scroll=new ScrollView(this);content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);scroll.addView(content);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));root.addView(button("Refresh",this::refresh));setContentView(root);render();}
 @Override protected void onResume(){super.onResume();foreground=true;handler.removeCallbacks(refreshTick);handler.post(refreshTick);}
 @Override protected void onPause(){foreground=false;handler.removeCallbacks(refreshTick);super.onPause();}
 @Override protected void onDestroy(){handler.removeCallbacksAndMessages(null);io.shutdownNow();super.onDestroy();}
 private JSONObject read(String path)throws Exception{if(!new HashSet<String>(Arrays.asList("/api/mining/public-work","/api/mining/earned-credits","/api/prices/zec?range=1m")).contains(path))throw new IOException("Endpoint refused");HttpsURLConnection c=(HttpsURLConnection)new URL("https://pointsixpool.com"+path).openConnection();c.setConnectTimeout(12000);c.setReadTimeout(12000);c.setInstanceFollowRedirects(false);c.setUseCaches(false);c.setRequestProperty("Accept","application/json");try{if(c.getResponseCode()!=200)throw new IOException("Feed pending");long deadline=System.nanoTime()+15000000000L;ByteArrayOutputStream bytes=new ByteArrayOutputStream();try(InputStream stream=c.getInputStream()){byte[] b=new byte[8192];int n;while((n=stream.read(b))!=-1){if(System.nanoTime()>deadline||bytes.size()+n>4194304)throw new IOException("Feed limit");bytes.write(b,0,n);}}return new JSONObject(bytes.toString(StandardCharsets.UTF_8.name()));}finally{c.disconnect();}}
 private boolean fresh(JSONObject x,String stamp,int age){double a=System.currentTimeMillis()/1000d-x.optDouble(stamp,Double.NaN);return x.optBoolean("available",false)&&Double.isFinite(a)&&a>=-5&&a<=age;}
 private void refresh(){if(busy||!foreground)return;String address=wallet.getText().toString().trim();if(!address.matches("t[13][1-9A-HJ-NP-Za-km-z]{33}")){workFresh=false;workers=new JSONArray();credit=price=null;status="Enter your public ZEC t1/t3 receiving address.";render();return;}busy=true;getPreferences(0).edit().putString("publicWallet",address).apply();io.execute(()->{JSONArray selected=new JSONArray();Double earned=null,usd=null;boolean freshWork=false;String note="Work feed awaiting update.";
 try{JSONObject x=read("/api/mining/public-work");if(!fresh(x,"observed_unix",90))throw new IOException();JSONArray list=x.getJSONArray("workers");if(list.length()>500)throw new IOException();for(int i=0;i<list.length();i++){JSONObject w=list.getJSONObject(i);double rate=w.optDouble("hashrate_5m",Double.NaN);if(address.equals(w.optString("wallet_address"))&&Double.isFinite(rate)&&rate>=0)selected.put(w);}freshWork=true;note="Updated "+new java.text.SimpleDateFormat("HH:mm:ss",Locale.UK).format(new Date());}catch(Exception ignored){}
 try{JSONObject x=read("/api/mining/earned-credits");if(!fresh(x,"observed_unix",90))throw new IOException();JSONArray list=x.getJSONArray("wallets");for(int i=0;i<list.length();i++){JSONObject w=list.getJSONObject(i);long zats=w.optLong("earned_all_zats",-1);if(address.equals(w.optString("wallet_address"))&&zats>=0&&zats<=2100000000000000L)earned=zats/100000000d;}}catch(Exception ignored){}
 try{JSONObject x=read("/api/prices/zec?range=1m");double p=x.optDouble("price",Double.NaN);if(fresh(x,"sample_time",900)&&Double.isFinite(p)&&p>0)usd=p;}catch(Exception ignored){}
 JSONArray finalWorkers=selected;Double finalEarned=earned,finalPrice=usd;boolean finalFresh=freshWork;String finalNote=note;handler.post(()->{busy=false;if(isFinishing()||isDestroyed()||!address.equals(wallet.getText().toString().trim()))return;workers=finalWorkers;credit=finalEarned;price=finalPrice;workFresh=finalFresh;status=finalNote;render();});});}
 private void render(){if(content==null)return;content.removeAllViews();
 content.addView(text(status,12));if("Income".equals(tab)){content.addView(text("Mining credits · all time",16));content.addView(text(credit==null?"Awaiting verified credits":String.format(Locale.UK,"%.8f ZEC",credit),25));if(credit!=null&&price!=null)content.addView(text(String.format(Locale.UK,"≈ $%.2f USD",credit*price),21));content.addView(text("Recorded wallet credits, not a withdrawable account balance. USD is a current valuation.",12));double rate=0;for(int i=0;i<workers.length();i++)rate+=workers.optJSONObject(i).optDouble("hashrate_5m",0);content.addView(text(workFresh?String.format(Locale.UK,"%d workers · %.2f Sol/s",workers.length(),rate):"Worker measurements awaiting update",16));return;}
 if(!workFresh){content.addView(text("Fresh worker measurements awaiting update",16));return;}if(workers.length()==0)content.addView(text("No published workers for this wallet in the recorded window.",14));for(int i=0;i<workers.length();i++){JSONObject w=workers.optJSONObject(i);boolean active=System.currentTimeMillis()/1000d-w.optLong("last_share_unix",0)<600;TextView title=text((active?"● ":"● ")+w.optString("worker_name","Worker"),18);title.setTextColor(active?Color.rgb(40,199,135):Color.rgb(244,99,99));content.addView(title);content.addView(text(String.format(Locale.UK,"%.2f Sol/s · 5m",w.optDouble("hashrate_5m",0)),14));content.addView(text(active?"Recent accepted work":"No recent accepted work; this alone does not prove disconnection.",12));JSONArray history=w.optJSONArray("history");if(history!=null)content.addView(new HistoryView(this,history),new LinearLayout.LayoutParams(-1,120));}}
 private static final class HistoryView extends View{
  final JSONArray samples;final android.graphics.Paint paint=new android.graphics.Paint(3);
  HistoryView(android.content.Context c,JSONArray s){super(c);samples=s;setContentDescription("Recorded worker hashrate history");}
  @Override protected void onDraw(android.graphics.Canvas canvas){super.onDraw(canvas);ArrayList<double[]> data=new ArrayList<>();double max=1,now=System.currentTimeMillis()/1000d;for(int i=0;i<Math.min(144,samples.length());i++){JSONObject s=samples.optJSONObject(i);if(s==null)continue;double t=s.optDouble("sampled_unix",Double.NaN),h=s.optDouble("hashrate",Double.NaN);if(Double.isFinite(t)&&Double.isFinite(h)&&h>=0&&t<=now-600){data.add(new double[]{t,h});max=Math.max(max,h);}}paint.setColor(Color.rgb(46,213,177));if(data.size()<2){paint.setTextSize(24);canvas.drawText("Awaiting recorded history",8,50,paint);return;}data.sort(Comparator.comparingDouble(a->a[0]));double start=data.get(0)[0],duration=Math.max(1,data.get(data.size()-1)[0]-start),previous=0;android.graphics.Path path=new android.graphics.Path();for(int i=0;i<data.size();i++){double[]s=data.get(i);float x=(float)((s[0]-start)/duration*getWidth()),y=(float)((1-s[1]/max)*(getHeight()-12)+6);if(i==0||s[0]-previous>600)path.moveTo(x,y);else path.lineTo(x,y);previous=s[0];}paint.setStyle(android.graphics.Paint.Style.STROKE);paint.setStrokeWidth(3);canvas.drawPath(path,paint);paint.setStyle(android.graphics.Paint.Style.FILL);}
 }
}
