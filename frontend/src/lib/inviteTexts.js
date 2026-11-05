// The words of the invitation letter (lib/invite.js), per assistant and in both languages: the problem it is built
// for, what it does about it, six gains, and the first step after logging in. GENERAL is the letter for two or more
// assistants. Written for showing the demo; a real customer's letter may say it differently.
const SETUP_FA = "در صفحه‌ی اول «تنظیمات پیش‌فرض» و سپس «ساخت دمو» را بزنید؛ بعد با هر نقشی که خواستید وارد شوید."
const SETUP_EN = "On the first page press «Default settings», then «Build the demo»; then sign in with any role you like."

export const GENERAL = {
  fa: {
    problem: "بیشتر کسب‌وکارهای ایرانی کارهای هر روزشان را با دفتر، اکسل، تلفن و حافظه‌ی افراد پیش می‌برند. اطلاعات در چند جا پخش است، کارها به یاد یک نفر بند است و همین باعث می‌شود مهلتی از دست برود، پولی دیر برسد یا مشتری‌ای بی‌پاسخ بماند.",
    solution: "دستیارهای پودینه هر کدام برای یک حرفه ساخته شده‌اند. داده‌های پراکنده را یک‌جا جمع می‌کنند، هر روز نشان می‌دهند چه کاری منتظر شماست و هر عدد را از داده‌های خود کسب‌وکار حساب می‌کنند. هوش مصنوعی فقط متن می‌نویسد و هر چیزی که از دفتر بیرون می‌رود یا تصمیم است، پیش از فرستادن به تأیید یک نفر می‌رسد.",
    gains: ["کارهای هر روز سبک‌تر.", "هیچ کاری فراموش نمی‌شود.", "عددهایی که می‌شود به آن‌ها اعتماد کرد.", "تصمیم همیشه با شماست.", "کار روی گوشی و رایانه.", "نصب روی رایانه‌ی خود شما."],
    start: SETUP_FA,
  },
  en: {
    problem: "Most businesses in Iran run their day on notebooks, Excel, the phone and people's memory. Information sits in several places and work depends on one person remembering it, so a deadline is missed, money arrives late or a customer goes unanswered.",
    solution: "Each Pudineh assistant is built for one trade. It brings scattered data together, shows every day what is waiting for you and works out every number from the business's own data. The AI only writes text, and anything that leaves the office or is a decision is approved by a person first.",
    gains: ["Lighter everyday work.", "Nothing is forgotten.", "Numbers you can trust.", "The decision is always yours.", "Works on phone and computer.", "Installed on your own computer."],
    start: SETUP_EN,
  },
}

export const TEXTS = {
  school: {
    fa: {
      problem: "در یک مدرسه، هر روز اطلاعات زیادی باید خوانده، پیگیری و به دست شخص درست رسانده شود: نامه‌ها و بخشنامه‌های اداره که هر کدام مهلت و کار خودش را دارد، حضور و غیاب دانش‌آموزان، تأخیر همکاران، نمره‌ها و وضعیت درسی هر دانش‌آموز، فرم‌های سلامت، پیام به اولیا و پرسش‌هایی که جوابشان در آیین‌نامه‌هاست. بیشتر این کارها دستی، پراکنده و وابسته به حافظه‌ی افراد است. نتیجه این است که مهلت یک نامه دیر دیده می‌شود، غیبت‌های پشت سر هم یک دانش‌آموز یا افت نمره‌اش تا وقتی جدی نشده به چشم مشاور نمی‌آید، تأخیرهای تکراری یک همکار ثبت می‌شود ولی کسی آن را جمع‌بندی نمی‌کند، و ولی از وضعیت فرزندش فقط در پایان ترم باخبر می‌شود.",
      solution: "دستیار مدرسه این اطلاعات پراکنده را یک‌جا جمع می‌کند و هر نکته را در زمان مناسب به شخص درست می‌رساند. هر صبح برای مدیر خلاصه‌ی کوتاهی از مهم‌ترین کارهای همان روز می‌نویسد. نامه‌های اداره را می‌خواند، دسته‌بندی می‌کند، پیش‌نویس پاسخ را با عددهای خود مدرسه آماده می‌کند و پیش از رسیدن مهلت یادآوری می‌کند. غیبت‌های پشت سر هم و افت نمره‌ی هر دانش‌آموز را خودش پیدا می‌کند و به مشاور نشان می‌دهد، و تأخیرهای تکراری همکاران را برای مدیر جمع‌بندی می‌کند. به هر ولی گزارش کوتاه هفتگی از وضعیت فرزند خودش می‌دهد و به پرسش همه درباره‌ی آیین‌نامه‌ها، با نام ماده‌ی مربوط، پاسخ می‌دهد. همه‌ی عددها از اطلاعات خود مدرسه می‌آیند و هر چیزی که از مدرسه بیرون می‌رود یا تصمیم است، اول به تأیید مدیر، مشاور یا کارمند دفتر می‌رسد.",
      gains: ["بازخورد سریع‌تر.", "برنامه‌ی روشن برای اقدام و پیگیری.", "توجه ویژه به دانش‌آموزانی که به کمک نیاز دارند.", "کمک به کیفیت آموزش و رضایت اولیا.", "کار سبک‌تر و رضایت بیشتر کارکنان و معلمان.", "تنش کمتر و پیگیری‌های کمتر میان اولیا و معلمان."],
      start: SETUP_FA,
    },
    en: {
      problem: "Every day a school has a great deal of information to read, follow up and get to the right person: letters and circulars from the education office, each with its own deadline, pupils' attendance, colleagues' late arrivals, marks and each pupil's progress, health forms, messages to parents and questions whose answers are in the regulations. Most of this work is done by hand, scattered, and depends on people's memory. So a letter's deadline is noticed too late, a pupil's repeated absences or falling marks reach the counselor only once they are serious, a colleague's repeated lateness is recorded but never added up, and parents hear how their child is doing only at the end of term.",
      solution: "The School Assistant brings this scattered information together and gets each point to the right person at the right time. Every morning it writes the principal a short summary of the day's most important work. It reads the education office's letters, sorts them, drafts replies with the school's own numbers and reminds before the deadline. It finds each pupil's repeated absences and falling marks and shows them to the counselor, and adds up colleagues' repeated lateness for the principal. It gives each parent a short weekly report on their own child and answers everyone's questions about the regulations, naming the article. Every number comes from the school's own data, and anything that leaves the school or is a decision is approved first by the principal, the counselor or the office.",
      gains: ["Faster feedback.", "A clear plan for action and follow-up.", "Special attention to pupils who need help.", "Better teaching and happier parents.", "Lighter work and happier staff and teachers.", "Less tension and back-and-forth between parents and teachers."],
      start: SETUP_EN,
    },
  },
  fabric: {
    fa: {
      problem: "یک عمده‌فروشی پارچه کارش را با سه فایل اکسل و تلفن پیش می‌برد: انبار، فروش و حساب‌ها. سفارش‌ها پشت تلفن گرفته می‌شود، چک‌ها و طلب‌ها در ذهن صاحب کار است و سه فایل با هم جور نیستند. چک برگشتی دیر دیده می‌شود، مشتری از سقف اعتبارش جلو می‌زند، پارچه‌ی پرفروش بی‌خبر تمام می‌شود و اگر فاکتوری گم شود یا صندوق شبی کم بیاید، کسی متوجه نمی‌شود.",
      solution: "دستیار پارچه‌فروشی همان سه فایل اکسل را می‌خواند و در آن‌ها می‌نویسد؛ لازم نیست کسی روش کارش را عوض کند. سفارش تلفنی را با موجودی و قیمت واقعی ثبت می‌کند و در هر سه فایل می‌نویسد. هر صبح چک‌های این هفته، طلب‌ها و پارچه‌هایی را که رو به تمام شدن‌اند نشان می‌دهد و سه فایل را با هم مقایسه می‌کند تا هر چیزی که جور نیست، با جمع و جزئیاتش پیدا شود. هر عدد «از کجا؟» دارد و هر تغییر با نام شخص و ساعت ثبت می‌شود.",
      gains: ["سفارش تلفنی سریع و بی‌خطا.", "چک برگشتی و طلب معوق در همان روز.", "خبر پیش از تمام شدن پارچه‌ی پرفروش.", "انبار، فروش و صندوق هر روز با هم جور.", "اعتماد بیشتر به عددها.", "وقت بیشتر برای مشتری‌ها."],
      start: SETUP_FA,
    },
    en: {
      problem: "A fabric wholesaler runs on three Excel files and the phone: stock, sales and accounts. Orders are taken over the phone, cheques and receivables live in the owner's head and the three files do not agree. A bounced cheque is noticed late, a customer goes past his credit limit, a best-selling fabric runs out without warning, and if an invoice goes missing or the till is short one evening, nobody notices.",
      solution: "The Fabric Wholesale Assistant reads the same three Excel files and writes into them; nobody has to change how they work. It takes a phone order with real stock and prices and writes it into all three files. Every morning it shows this week's cheques, what is owed and the fabrics about to run out, and it compares the three files so that whatever does not add up is found, with the sum and the details. Every number has «where from?», and every change is recorded with a name and a time.",
      gains: ["Quick, error-free phone orders.", "Bounced cheques and overdue debts the same day.", "Warning before a best-seller runs out.", "Stock, sales and till agree every day.", "More trust in the numbers.", "More time for customers."],
      start: SETUP_EN,
    },
  },
  estate: {
    fa: {
      problem: "فایل‌های یک بنگاه در دفترها، گوشی مشاوران و گروه‌های پیام‌رسان پخش است. فایلی دو بار ثبت می‌شود یا واحد فروخته‌شده هنوز پیشنهاد می‌شود، متقاضی از حافظه با فایل‌ها جور می‌شود، قیمت حدسی گفته می‌شود و مالک هفته‌ها بی‌خبر می‌ماند. گاهی هم معامله دور از بنگاه انجام می‌شود و کسی نمی‌فهمد.",
      solution: "دستیار بنگاه فایل یا درخواست را از هر متنی، آگهی دیوار، پیام واتس‌اپ یا یادداشت تماس، می‌خواند و پیش از ثبت، فایل‌های شبیه را نشان می‌دهد. برای هر فایل متقاضی مناسب و برای هر متقاضی فایل مناسب را پیدا می‌کند، قیمت را با معامله‌های خود بنگاه در همان محله می‌سنجد و گزارش کوتاه به مالک را آماده می‌کند. سایت بنگاه هم مشتری جدید را مستقیم به نوبت مشاوران می‌دهد.",
      gains: ["هیچ فایلی گم یا تکراری نمی‌شود.", "متقاضی مناسب در همان روز.", "قیمت بر پایه‌ی معامله‌های واقعی.", "مالکان همیشه در جریان.", "دیدن معامله‌ای که دور از بنگاه انجام شده است.", "مشتری جدید از سایت بنگاه."],
      start: SETUP_FA,
    },
    en: {
      problem: "An agency's listings are scattered across notebooks, agents' phones and chat groups. A listing is entered twice or a sold unit is still offered, buyers are matched from memory, prices are guessed and owners hear nothing for weeks. Sometimes a deal is made around the agency and nobody notices.",
      solution: "The Real Estate Agency Assistant reads a listing or a request from any text, a Divar ad, a WhatsApp message or call notes, and shows look-alike listings before saving. It finds the right buyer for every listing and the right listing for every buyer, checks the price against the agency's own deals in that neighbourhood and prepares a short report for the owner. The agency's website passes new customers straight to the agents in turn.",
      gains: ["No listing lost or entered twice.", "The right buyer the same day.", "Prices based on real deals.", "Owners always kept informed.", "Deals made around the agency come to light.", "New customers from the agency's website."],
      start: SETUP_EN,
    },
  },
  law: {
    fa: {
      problem: "هر ابلاغیه‌ای که از سامانه‌ی ثنا می‌رسد یک مهلت را شروع می‌کند، و این مهلت‌ها در دفترچه یا ذهن وکیل و منشی است. حساب روز آخر با جمعه‌ها و تعطیلات ساده نیست، ابلاغیه‌ای دیر ثبت می‌شود، پرونده‌ای ماه‌ها بی‌کار می‌ماند و موکل از وضع پرونده‌اش بی‌خبر است. یک مهلت از دست‌رفته می‌تواند یک دعوا را از دست بدهد.",
      solution: "دستیار دفتر وکالت متن ابلاغیه را می‌خواند، نوع، شماره‌ی پرونده و تاریخ ابلاغ را از آن بیرون می‌کشد و روز آخر هر مهلت را با جمعه‌ها و تعطیلات رسمی حساب می‌کند؛ کنار هر مهلت نوشته است چطور حساب شده است. هر صبح مهلت‌های نزدیک، جلسه‌های فردا و پرونده‌های بی‌کار را نشان می‌دهد و گزارش کوتاه به موکل را از روی ابلاغیه‌های پرونده آماده می‌کند تا وکیل بخواند و بفرستد.",
      gains: ["هیچ مهلتی از دست نمی‌رود.", "روز آخر هر مهلت با تعطیلات.", "جلسه‌ی فردا از امروز روشن است.", "موکلان همیشه در جریان.", "پرونده‌ی بی‌کار دیده می‌شود.", "خیال آسوده‌ی وکیل و همکاران."],
      start: SETUP_FA,
    },
    en: {
      problem: "Every notice from the courts' system starts a deadline, and these deadlines live in a notebook or in the heads of the lawyer and the secretary. Working out the last day around Fridays and holidays is not simple, a notice is entered late, a case sits idle for months and the client hears nothing. One missed deadline can lose a case.",
      solution: "The Law Office Assistant reads a notice's text, takes out its kind, the case number and the date of service, and works out the last day of every deadline around Fridays and official holidays, showing how it was counted. Every morning it shows the deadlines coming up, tomorrow's hearings and idle cases, and it drafts a short report to the client from the case's notices for the lawyer to read and send.",
      gains: ["No deadline missed.", "The last day of every deadline, holidays counted.", "Tomorrow's hearing clear from today.", "Clients always kept informed.", "Idle cases come to light.", "Peace of mind for the lawyer and colleagues."],
      start: SETUP_EN,
    },
  },
  dental: {
    fa: {
      problem: "در یک مطب، هر صندلی خالی درآمد از دست‌رفته است. نوبت‌ها در دفتر منشی است، تأیید نوبت فردا فراموش می‌شود، بیماری که زیاد نمی‌آید دوباره نوبت می‌گیرد و وقتی نوبتی لغو می‌شود، کسی سراغ فهرست انتظار نمی‌رود. طرح‌های درمانی که پس از معاینه پیشنهاد شده‌اند، اگر کسی پیگیری نکند، هرگز شروع نمی‌شوند.",
      solution: "دستیار مطب هر روز نوبت‌های تأییدنشده‌ی فردا را با پیام یادآوری آماده نشان می‌دهد، وقت خالی را به نفر بعدی فهرست انتظار پیشنهاد می‌کند و بیمارانی را که زیاد نمی‌آیند پیش از نوبتشان یادآوری می‌کند. طرح‌های درمانی شروع‌نشده را با مبلغشان پیدا می‌کند و پیام پیگیری مؤدبانه‌ای آماده می‌کند که منشی بخواند و بفرستد. مانده‌ی حساب هر بیمار هم همیشه روشن است.",
      gains: ["صندلی خالی کمتر.", "نوبت‌های فردا تأییدشده.", "طرح درمانی که فراموش نمی‌شود.", "فهرست انتظاری که به کار می‌آید.", "حساب روشن هر بیمار.", "کار سبک‌تر برای منشی."],
      start: SETUP_FA,
    },
    en: {
      problem: "In a clinic, every empty chair is lost income. Appointments live in the secretary's book, confirming tomorrow's patients is forgotten, a patient who often fails to come books again, and when an appointment is cancelled nobody turns to the waiting list. Treatment plans proposed after an exam never start if nobody follows them up.",
      solution: "The Dental Clinic Assistant shows tomorrow's unconfirmed appointments every day with a reminder ready, offers a freed hour to the next person on the waiting list and reminds patients who often miss appointments before theirs. It finds treatment plans not yet started, with their value, and drafts a polite follow-up for the secretary to read and send. Every patient's balance is always clear.",
      gains: ["Fewer empty chairs.", "Tomorrow's appointments confirmed.", "Treatment plans not forgotten.", "A waiting list that works.", "A clear balance for every patient.", "Lighter work for the secretary."],
      start: SETUP_EN,
    },
  },
  lang: {
    fa: {
      problem: "جدول کلاس‌های یک آموزشگاه زبان روی کاغذ یا در اکسل است. استادی در یک ساعت دو کلاس می‌گیرد، کلاسی از اتاقش پرتر می‌شود و ثبت‌نام ترم بعد تا روزهای آخر روشن نیست. زبان‌آموز نمی‌داند ترم بعد چه کتابی بخرد و تا کجای مسیر مانده است، و غیبت‌های پشت سر هم یا شهریه‌ی مانده دیر دیده می‌شود.",
      solution: "دستیار آموزشگاه جدول کلاس‌ها را با یک قاعده می‌سنجد: اتاق، استاد، ساعت‌هایی که استاد می‌آید و جای هر اتاق. برای جابه‌جا کردن هر کلاس، خانه‌های آزاد را سبز نشان می‌دهد و پیام تغییر را برای زبان‌آموزان آماده می‌کند. آزمون تعیین سطح و آزمون‌های آنلاین را خود برنامه نمره می‌دهد، و هر زبان‌آموز مسیرش، کتاب این ترم و ترم بعد و برنامه‌ی هفته‌اش را می‌بیند.",
      gains: ["جدول کلاس بدون تداخل.", "ثبت‌نام ترم بعد پیش از پایان ترم.", "آزمون آنلاین با نمره‌ی خودکار.", "مسیر روشن برای هر زبان‌آموز.", "حضور و غیاب در چند ثانیه.", "شهریه‌ی مانده در همان روز."],
      start: SETUP_FA,
    },
    en: {
      problem: "A language institute's timetable lives on paper or in Excel. A teacher gets two classes at one hour, a class outgrows its room and next term's registration is unclear until the last days. Learners do not know which book to buy next term or how far they have to go, and repeated absences or unpaid fees are noticed late.",
      solution: "The Language Institute Assistant checks the timetable with one rule: the room, the teacher, the hours the teacher comes and the seats in each room. To move a class it shows the free cells in green and drafts the message for its learners. The placement test and online tests are marked by the program, and every learner sees their road, this term's and next term's book and their plan for the week.",
      gains: ["A timetable without clashes.", "Next term's registration before the term ends.", "Online tests marked automatically.", "A clear road for every learner.", "Attendance in a few seconds.", "Unpaid fees seen the same day."],
      start: SETUP_EN,
    },
  },
  hotel: {
    fa: {
      problem: "در روزهای شلوغ یک هتل، رزروها از تلفن، واتس‌اپ، آژانس‌ها و سایت‌های رزرو می‌رسد. اتاقی دو بار فروخته می‌شود، مهمان ویژه به اتاق آماده‌نشده می‌رسد، بیعانه‌ای نمی‌رسد و کسی پیگیری نمی‌کند و قیمت هر شب با فصل و آخر هفته هر بار دستی حساب می‌شود. پایان روز هم صندوق با فروش جور نیست.",
      solution: "دستیار هتل رزرو تا تسویه را در یک پنل جمع می‌کند. قیمت هر شب را با فصل، آخر هفته و وعده‌ها حساب می‌کند، بهترین اتاق را پیشنهاد می‌دهد و جدول اتاق‌ها و وضعیت خانه‌داری را یک‌جا نشان می‌دهد. در روزهای شلوغ فهرستی می‌دهد که می‌گوید اول چه کاری. سایت هتل رزرو موقت و رسید بیعانه را می‌گیرد و پذیرش فقط تأیید می‌کند.",
      gains: ["هیچ اتاقی دو بار فروخته نمی‌شود.", "اتاق آماده برای هر ورود.", "قیمت درست برای هر شب.", "بیعانه‌ای که از یاد نمی‌رود.", "صندوق جور با فروش.", "رزرو مستقیم از سایت هتل."],
      start: SETUP_FA,
    },
    en: {
      problem: "On a hotel's busy days, bookings come by phone, WhatsApp, agencies and booking sites. A room is sold twice, a VIP arrives to a room that is not ready, a deposit never comes and nobody chases it, and each night's price with season and weekend is worked out by hand every time. At the end of the day the till does not match the sales.",
      solution: "The Hotel Assistant brings reservation to check-out into one panel. It works out each night's price with season, weekend and meals, suggests the best room and shows the room chart and housekeeping in one place. On busy days it gives a list of what to do first. The hotel's website takes tentative bookings and deposit receipts, and the front desk only confirms.",
      gains: ["No room sold twice.", "A ready room for every arrival.", "The right price for every night.", "No deposit forgotten.", "A till that matches the sales.", "Direct bookings from the hotel's website."],
      start: SETUP_EN,
    },
  },
  lodge: {
    fa: {
      problem: "یک اقامتگاه بوم‌گردی مهمانانش را از اینستاگرام، واتس‌اپ و تلفن می‌گیرد. شب‌های خالی فقط در ذهن میزبان است، پاسخ هر پیام وقت می‌گیرد، رسید بیعانه در پیام‌ها گم می‌شود و نظر مهمانان پس از سفر جایی ثبت نمی‌شود.",
      solution: "دستیار اقامتگاه به اقامتگاه یک سایت عمومی می‌دهد: مهمان شب‌های خالی و قیمت‌ها را می‌بیند، حساب می‌سازد، درخواست رزرو و رسید بیعانه می‌فرستد و پس از سفر نظر می‌دهد. میزبان همه را از یک پنل می‌گرداند: درخواست را تأیید می‌کند، رسید را می‌بیند و نظرها را پیش از نمایش می‌خواند.",
      gains: ["رزرو مستقیم بدون واسطه.", "شب‌های خالی جلوی چشم مهمان.", "رسید بیعانه‌ای که گم نمی‌شود.", "نظر واقعی مهمانان.", "پاسخ کمتر به پیام‌های تکراری.", "یک پنل برای همه‌ی کارها."],
      start: SETUP_FA,
    },
    en: {
      problem: "An eco-lodge gets its guests through Instagram, WhatsApp and the phone. Free nights exist only in the host's head, every message takes time to answer, deposit receipts get lost in chats and guests' reviews after their stay are never recorded.",
      solution: "The Eco-lodge Assistant gives the lodge a public website: guests see free nights and prices, make an account, send a booking request and a deposit receipt, and review after their stay. The host runs it all from one panel: approves requests, checks receipts and reads reviews before they are shown.",
      gains: ["Direct bookings, no middleman.", "Free nights in front of guests.", "Deposit receipts never lost.", "Real reviews from guests.", "Fewer repeated questions to answer.", "One panel for everything."],
      start: SETUP_EN,
    },
  },
  deed: {
    fa: {
      problem: "تبدیل سندهای دفترچه‌ای به سند تک‌برگ یعنی خواندن صفحه‌های اسکن‌شده و نوشتن دوباره‌ی داده‌هایشان: نام مالکان، کد ملی، سهم‌ها، پلاک و تاریخ‌ها. این کار دستی، کند و پرخطاست؛ یک رقم اشتباه در کد ملی یا سهم‌هایی که جمعشان شش دانگ نمی‌شود، بعدها گرفتاری می‌سازد.",
      solution: "دستیار استخراج داده‌ی سند، تصویر یا PDF سند را روی خود سرور می‌خواند و داده‌هایش را بیرون می‌کشد. هر مقدار را در متن صفحه پیدا می‌کند و سطر آن را کنارش نشان می‌دهد؛ اگر پیدا نشود، خالی می‌ماند و حدس زده نمی‌شود. کد ملی، تاریخ‌ها و جمع سهم‌ها بررسی می‌شود و کارشناس پیش از تأیید، داده‌ها را کنار تصویر سند می‌بیند.",
      gains: ["کار سریع‌تر برای کارشناس.", "خطای کمتر در داده‌ها.", "هر مقدار با جای آن در سند.", "بررسی کد ملی و جمع سهم‌ها.", "پردازش روی سرور خود سازمان.", "تأیید نهایی با کارشناس."],
      start: "یکی از سندهای نمونه را انتخاب کنید یا تصویر سند خودتان را بفرستید.",
    },
    en: {
      problem: "Turning booklet deeds into single-page deeds means reading scanned pages and typing their data again: owners' names, national IDs, shares, plot numbers and dates. It is manual, slow and error-prone; one wrong digit in a national ID or shares that do not add up to six dang cause trouble later.",
      solution: "The Deed Data Extraction Assistant reads the deed's image or PDF on the server itself and takes out its data. It finds every value in the page's text and shows its line beside it; if it is not found, it stays empty and is never guessed. National IDs, dates and the sum of shares are checked, and the reviewer sees the data next to the deed's image before approving.",
      gains: ["Faster work for the reviewer.", "Fewer errors in the data.", "Every value with its place in the deed.", "National IDs and shares checked.", "Processed on the organization's own server.", "Final approval by the reviewer."],
      start: "Pick one of the sample deeds or send an image of your own.",
    },
  },
}
