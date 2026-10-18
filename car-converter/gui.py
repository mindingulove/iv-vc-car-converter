from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,colorchooser
import threading,subprocess,sys,json,re,hashlib
from convert_car import ROOT,DEFAULT_RUNTIME,car_rows
from paint_options import resolve_runtime,channel_name

class ConverterWindow:
 def __init__(self,root):
  self.root=root;root.title('Vice City Car Converter');root.geometry('1080x850');self.source=tk.StringVar();self.mode=tk.StringVar(value='add');self.name=tk.StringVar(value='custom_car');self.traffic=tk.BooleanVar(value=True);self.frequency=tk.IntVar(value=5);self.status=tk.StringVar(value='Select a WFT + matching WTD, or a NextGen vehicles.img archive.');self.entries=[];self.lastoutput=None;self.busy=False;self.autofit=tk.BooleanVar(value=True);self.rideheight=tk.DoubleVar(value=0);self.stiffness=tk.DoubleVar(value=1);self.damping=tk.DoubleVar(value=1);self.travel=tk.DoubleVar(value=1)
  outer=ttk.Frame(root);outer.pack(fill='both',expand=True);canvas=tk.Canvas(outer,highlightthickness=0);scroll=ttk.Scrollbar(outer,orient='vertical',command=canvas.yview);canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
  panel=ttk.Frame(canvas,padding=16);window=canvas.create_window(0,0,window=panel,anchor='nw');panel.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width));root.bind('<MouseWheel>',lambda e:canvas.yview_scroll(-1 if e.delta>0 else 1,'units'));panel.columnconfigure(1,weight=1);panel.rowconfigure(10,weight=1)
  ttk.Label(panel,text='Vice City Car Converter',font=('',19,'bold')).grid(row=0,column=0,columnspan=4,sticky='w',pady=(0,12))
  ttk.Label(panel,text='Source car / archive').grid(row=1,column=0,sticky='w');ttk.Entry(panel,textvariable=self.source).grid(row=1,column=1,columnspan=2,sticky='ew',padx=8);ttk.Button(panel,text='Browse…',command=self.browse).grid(row=1,column=3)
  self.selection=ttk.Combobox(panel,state='readonly');self.selection.grid(row=2,column=1,columnspan=2,sticky='ew',padx=8,pady=8);ttk.Button(panel,text='Read models',command=self.read_models).grid(row=2,column=3);ttk.Label(panel,text='Archive model').grid(row=2,column=0,sticky='w')
  modes=ttk.Frame(panel);modes.grid(row=3,column=0,columnspan=4,sticky='ew',pady=12);ttk.Radiobutton(modes,text='Add a new car',variable=self.mode,value='add',command=self.update_mode).pack(side='left');ttk.Radiobutton(modes,text='Replace an existing car',variable=self.mode,value='replace',command=self.update_mode).pack(side='left',padx=24)
  ttk.Label(panel,text='New car name').grid(row=4,column=0,sticky='w');self.nameentry=ttk.Entry(panel,textvariable=self.name);self.nameentry.grid(row=4,column=1,sticky='ew',padx=8)
  rows=car_rows(DEFAULT_RUNTIME);self.cars=sorted({r[1] for key,r in rows.items() if 130<=key<=236});self.donor=ttk.Combobox(panel,values=self.cars,state='readonly');self.donor.set('rancher');self.donor.grid(row=4,column=3,sticky='ew');self.donorlabel=ttk.Label(panel,text='Handling / collision donor');self.donorlabel.grid(row=4,column=2,sticky='e',padx=8)
  ttk.Checkbutton(panel,text='Include in normal traffic',variable=self.traffic).grid(row=5,column=0,columnspan=2,sticky='w',pady=8);ttk.Label(panel,text='Traffic frequency').grid(row=5,column=2,sticky='e');ttk.Spinbox(panel,from_=1,to=30,textvariable=self.frequency,width=8).grid(row=5,column=3,sticky='w')
  tuning=ttk.LabelFrame(panel,text='Suspension (per converted car)',padding=8);tuning.grid(row=6,column=0,columnspan=4,sticky='ew',pady=6)
  ttk.Checkbutton(tuning,text='Centre suspension on imported wheels',variable=self.autofit).grid(row=0,column=0,columnspan=2,sticky='w')
  for i,(label,var,low,high,step) in enumerate([('Ride height cm (+ raises)',self.rideheight,-30,30,1),('Spring strength ×',self.stiffness,.25,4,.05),('Damping ×',self.damping,.25,4,.05),('Travel ×',self.travel,.25,2,.05)]):
   ttk.Label(tuning,text=label).grid(row=1,column=i*2,sticky='w',padx=4);ttk.Spinbox(tuning,textvariable=var,from_=low,to=high,increment=step,width=6).grid(row=1,column=i*2+1)
  ttk.Button(tuning,text='Tune installed car…',command=self.tune_installed).grid(row=0,column=4,columnspan=4,sticky='e')
  buttons=ttk.Frame(panel);buttons.grid(row=7,column=0,columnspan=4,sticky='ew');self.convertbutton=ttk.Button(buttons,text='Convert and preview',command=self.convert);self.convertbutton.pack(side='left');self.installbutton=ttk.Button(buttons,text='Install converted car',command=self.install,state='disabled');self.installbutton.pack(side='left',padx=10);ttk.Button(buttons,text='Extract archive(s)…',command=self.extract_all).pack(side='left',padx=10)
  ttk.Label(panel,textvariable=self.status,wraplength=900).grid(row=8,column=0,columnspan=4,sticky='w',pady=8)
  self.preview=ttk.Label(panel,text='Preview appears here after conversion.');self.preview.grid(row=9,column=0,columnspan=4,sticky='ew')
  self.log=tk.Text(panel,height=10,wrap='word');self.log.grid(row=10,column=0,columnspan=4,sticky='nsew',pady=8)
  ttk.Label(panel,text='Four-wheel GTA IV / NextGen RSC5 cars. Other formats and unsupported rigs are rejected. Install while Vice City is closed.',wraplength=900).grid(row=11,column=0,columnspan=4,sticky='w')
  # Keep runtime selection and colour controls separate from source/model choices.
  self.runtime=tk.StringVar(value=str(DEFAULT_RUNTIME));self.paint_choices={};self.runtime_bound=None
  runtimebar=ttk.LabelFrame(panel,text='Target game folder',padding=6);runtimebar.grid(row=12,column=0,columnspan=4,sticky='ew');runtimebar.columnconfigure(0,weight=1)
  ttk.Entry(runtimebar,textvariable=self.runtime).grid(row=0,column=0,sticky='ew');ttk.Button(runtimebar,text='Choose game folder…',command=self.choose_runtime).grid(row=0,column=1)
  self.paintpanel=ttk.LabelFrame(panel,text='Car colours — convert first to detect the available channels',padding=6);self.paintpanel.grid(row=13,column=0,columnspan=4,sticky='ew')
  self.update_mode()
 def choose_runtime(self):
  value=filedialog.askdirectory(title='Choose game folder (or its Modloader folder)',initialdir=self.runtime.get())
  if not value:return
  try:
   runtime=resolve_runtime(value);cars=sorted({r[1] for r in car_rows(runtime).values()})
   if not cars:raise ValueError('No car definitions found in this game folder.')
   self.runtime.set(str(runtime));self.cars=cars;self.donor.configure(values=cars)
   if self.donor.get() not in cars:self.donor.set(cars[0])
   self.status.set('Modloader found: '+str(runtime/'modloader'))
  except ValueError as e:messagebox.showerror('Invalid game folder',str(e))
 def paint_args(self):
  return [item for channel,color in sorted(self.paint_choices.items()) for item in ('--paint',str(channel)+'='+color)]
 def show_paint(self):
  for child in self.paintpanel.winfo_children():child.destroy()
  report=json.loads((self.lastoutput/'conversion.json').read_text());self.paint_choices={int(k):'#'+bytes(v).hex() for k,v in report.get('paintColors',{}).items()}
  channels=report.get('detectedPaintChannels',[])
  self.paintpanel.configure(text='Detected car colours (conversion-time colours; source liveries/interiors preserved)')
  for i,channel in enumerate(channels):
   text=tk.StringVar(value=channel_name(channel)+': '+self.paint_choices.get(channel,'Source / donor'))
   def choose(c=channel,label=text):
    color=colorchooser.askcolor(color=self.paint_choices.get(c,'#808080'),title=channel_name(c))[1]
    if color:self.paint_choices[c]=color;label.set(channel_name(c)+': '+color)
   ttk.Button(self.paintpanel,textvariable=text,command=choose).grid(row=i//4,column=i%4,sticky='ew',padx=4,pady=3)
  if channels:
   ttk.Button(self.paintpanel,text='Apply colours and update preview',command=self.apply_paint).grid(row=(len(channels)+3)//4,column=0,columnspan=2)
   ttk.Button(self.paintpanel,text='Restore source / donor colours',command=lambda:self.apply_paint(True)).grid(row=(len(channels)+3)//4,column=2,columnspan=2)
  else:ttk.Label(self.paintpanel,text='No independent repaintable channels detected; authored finish stays intact.').pack()
 def apply_paint(self,reset=False):
  if not self.lastoutput:return
  if reset:self.paint_choices={}
  cmd=[sys.executable,Path(__file__).with_name('convert_car.py'),'--recolor-package',self.lastoutput,*self.paint_args()]
  self.status.set('Updating selected paint channels and validating…');self.process(cmd,self.converted_preview)
 def converted_preview(self):
  from PIL import Image,ImageTk
  image=Image.open(self.lastoutput/'preview.png');image.thumbnail((900,240));self.photo=ImageTk.PhotoImage(image);self.preview.configure(image=self.photo,text='');self.installbutton.configure(state='normal');self.show_paint();self.status.set('Validated. Review the preview, then install while the game is closed.')
 def update_mode(self):
  adding=self.mode.get()=='add';self.nameentry.configure(state='normal' if adding else 'disabled');self.donorlabel.configure(text='Handling / collision donor' if adding else 'Car to replace')
 def browse(self):
  name=filedialog.askopenfilename(title='Choose a car model or archive',filetypes=[('Car model/archive','*.wft *.img'),('All files','*')])
  if name:self.source.set(name);self.read_models()
 def append(self,text):self.log.insert('end',text+'\n');self.log.see('end')
 def read_models(self):
  path=Path(self.source.get()).expanduser()
  if not path.exists():messagebox.showerror('Source missing','Choose an existing .wft file or vehicles.img archive.');return
  if path.suffix.lower()=='.wft':self.entries=[];self.selection.configure(values=[path.stem]);self.selection.current(0);return
  self.status.set('Reading resource names and texture hints…')
  def work():
   try:
    from resource_input import scan,models
    selected=path
    if selected.is_dir():
     archives=list(selected.rglob('vehicles.img'))
     if len(archives)!=1:raise ValueError('Select one edition folder or one exact vehicles.img file.')
     selected=archives[0]
    es,_,_=scan(selected,ROOT/'cache'/(hashlib.sha256(str(selected.resolve()).encode()).hexdigest()[:16]+'.json'));entries=models(es)
    self.root.after(0,lambda:self.got_models(entries))
   except Exception as e:self.root.after(0,lambda error=str(e):messagebox.showerror('Cannot read source',error))
  threading.Thread(target=work,daemon=True).start()
 def got_models(self,entries):
  self.entries=entries;self.selection.configure(values=[f"{e['index']}: {e['name']} — {', '.join(e['textureHints'][:2])}" for e in entries]);self.selection.current(0);self.status.set(f'{len(entries)} model entries found. Embedded names can differ from the actual car: check the converted preview.')
 def process(self,cmd,on_success):
  if self.busy:return
  self.busy=True;self.convertbutton.configure(state='disabled');self.installbutton.configure(state='disabled')
  def work():
   try:
    p=subprocess.Popen(list(map(str,cmd)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    for line in p.stdout:self.root.after(0,lambda text=line.rstrip():self.append(text))
    code=p.wait();self.root.after(0,lambda:self.finished(code,on_success))
   except Exception as e:self.root.after(0,lambda error=str(e):self.failed(error))
  threading.Thread(target=work,daemon=True).start()
 def failed(self,error):self.busy=False;self.convertbutton.configure(state='normal');self.status.set(error);messagebox.showerror('Conversion failed',error)
 def finished(self,code,on_success):
  self.busy=False;self.convertbutton.configure(state='normal')
  if code:self.status.set('Stopped. See the log above; no new installation was made.');self.installbutton.configure(state='normal' if self.lastoutput else 'disabled');return
  self.installbutton.configure(state='normal' if self.lastoutput else 'disabled');on_success()
 def convert(self):
  source=self.source.get().strip()
  if not source:messagebox.showerror('Missing source','Select a model or archive first.');return
  adding=self.mode.get()=='add';target=self.donor.get();name=re.sub('[^a-z0-9_]','_',self.name.get().strip().lower()).strip('_') if adding else target;output=ROOT/'exports'/name
  cmd=[sys.executable,Path(__file__).with_name('convert_car.py'),'--source',source,'--mode',self.mode.get(),'--name',name,'--donor',target,'--replace',target,'--output',output,'--frequency',str(self.frequency.get())]
  try:runtime=resolve_runtime(self.runtime.get())
  except ValueError as e:messagebox.showerror('Invalid game folder',str(e));return
  cmd+=['--runtime',str(runtime),*self.tuning_args()]
  if self.entries:
   index=self.selection.current()
   if index<0:messagebox.showerror('Select a model','Select an archive model.');return
   cmd+=['--entry',str(self.entries[index]['index'])]
  if not self.traffic.get():cmd+=['--no-traffic']
  self.status.set('Converting, rendering a preview and validating through Metal…')
  def success():
   self.lastoutput=output;self.runtime_bound=runtime;self.converted_preview()
  self.process(cmd,success)
 def tuning_args(self):
  args=['--ride-height',str(self.rideheight.get()),'--stiffness',str(self.stiffness.get()),'--damping',str(self.damping.get()),'--travel',str(self.travel.get())]
  if not self.autofit.get():args+=['--no-auto-fit']
  return args
 def tune_installed(self):
  folder=filedialog.askdirectory(title='Select installed Converted car folder',initialdir=Path(self.runtime.get())/'modloader')
  if not folder:return
  if not (Path(folder)/'conversion.json').exists():messagebox.showerror('Choose a converted car','Select a Converted car folder containing conversion.json.');return
  cmd=[sys.executable,Path(__file__).with_name('convert_car.py'),'--tune-package',folder,'--runtime',self.runtime.get(),*self.tuning_args()]
  self.status.set('Applying suspension controls to selected car; Vice City must be closed.');self.process(cmd,lambda:self.status.set('Suspension saved. Restart Vice City to use the new settings.'))
 def extract_all(self):
  if not self.source.get().strip():messagebox.showerror('Choose an archive','Select a vehicles.img archive or paste a pack folder first.');return
  output=filedialog.askdirectory(title='Choose extraction output folder')
  if not output:return
  cmd=[sys.executable,Path(__file__).with_name('convert_car.py'),'--source',self.source.get().strip(),'--extract-all','--output',output]
  self.status.set('Extracting all native models and texture dictionaries…');self.process(cmd,lambda:self.status.set('Extraction complete. Source archives are unchanged; see manifests in '+output))
 def install(self):
  if not self.lastoutput:return
  cmd=[sys.executable,Path(__file__).with_name('convert_car.py'),'--install-package',self.lastoutput,'--runtime',self.runtime.get()]
  self.status.set('Installing validated Modloader package…');self.process(cmd,lambda:self.status.set('Installed. The car will be available after you restart Vice City.'))

def start():
 root=tk.Tk();ConverterWindow(root);root.mainloop()
