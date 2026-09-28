# 🏆 MT Model Arena — Official Comparative Leaderboard

تم توليد هذا الجدول آلياً بناءً على قياسات الأداء الفعلي لنماذج الترجمة في حلبة الاختبار الحية على بطاقات 24GB VRAM.

| الترتيب | اسم النموذج | المحرك | استهلاك VRAM | زمن P50 (ms) | أسرع جملة (ms) | السرعة (Tokens/s) | الهلوسة | تسريب الهوية | التقييم |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 🥇 | **tencent/Hy-MT2-7B** | `transformers` | 15.4 / 24 GB | **750.8 ms** | 65.7 ms | **30.3 t/s** | ✅ 0/20 | ✅ 0/20 | 🟢 Pass (Safe) |
| 🥈 | **google/gemma-4-E4B-it** | `transformers` | 15.3 / 24 GB | **1452.0 ms** | 171.7 ms | **16.1 t/s** | ✅ 0/20 | ⚠️ 1/20 | 🟢 Pass (Safe) |

---

## 🔍 مقارنة وتحليل العينات الصعبة (Canonical Cases Breakdown)

### 📌 النموذج: `tencent/Hy-MT2-7B`

| التصنيف | النص الأصلي | الترجمة الناتجة | زمن الاستجابة | الحالة |
| :--- | :--- | :--- | :---: | :---: |
| Saudi Podcast Compound | هذه الجملة اللي كنا دائماً نسمعها بشكل كبير: البعض يعتقد إنه أنا اليوم عشان أتعلم لازم يكون عندي كتاب وأقعد أقرأ، ولا إني أقعد مع على قولة كوتش. | This is a sentence we used to hear very often: Some people think that in order to learn today, I must have a book and sit down to read, or as Coach says, I must sit with it. | 1552.8 ms | ✅ OK |
| Saudi Podcast Dialogue | هل الصحيح في كلمة تعلّم إني أنا أجي أقول والله باخذ كتاب وأقرأ، ولا أروح لمدرب، ولا أجلس في فصل ومجموعة تعليم؟ ولا المفروض إنه الحياة مدرسة وأيضاً التجربة مدرسة؟ | Is it correct that when it comes to learning, I just say “I’ll take a book and read,” without going to a tutor or sitting in a classroom or study group? Isn’t it supposed to be that life is a school, and experience is also a school? | 1740.2 ms | ✅ OK |
| Saudi Podcast Nuance | الخبير لا، تلقاه يقول لك وش اللي يشتغل واللي ما يشتغل في كلام المختصين، لأنه صاحب تجربة وصاحب ميدان. | The expert, no—he’ll tell you what works and what doesn’t in the language of specialists, because he has experience and is on the ground. | 1021.5 ms | ✅ OK |
| Saudi Workplace Dialect | الناس في المقابلات الوظيفية يجي يقول لك أنا شغوف وأنا أتعلم بسرعة، بس بالواقع أول ما تحطه بمشروع حقيقي يضيع وما يعرف يتصرف. | In job interviews, people say they're passionate and learn quickly, but in reality, once you put them on a real project, they get lost and don't know what to do. | 1276.8 ms | ✅ OK |
| Jordanian Street Dialect | وين رايح هسا بنص النهار والدنيا شوب؟ استناني شوي بمر عالصيدلية وبعدين بلحقك عالفندق. | Where am I going at noon with all this chaos? Wait for me a bit at the pharmacy, and then I’ll meet you at the hotel. | 960.4 ms | ✅ OK |
| Levantine Cultural Idiom | حقك علي، مسحها بهاللحية وهاي المرة عدّيها بلا عصبية. | You’re right against me; wipe it with this beard, and this time count it without getting annoyed. | 750.8 ms | ✅ OK |
| Jordanian Travel Stress | الطيارة ما أمداني ألحقها وراحت علي والله، هسا شو أعمل بالمطار؟ | The plane didn’t give me time to catch up with it; it left me behind, I swear. What am I supposed to do at the airport now? | 1120.2 ms | ✅ OK |
| Gulf Politeness Slang | أبشر بعزك، ما طلبت شي يا غالي، كل أمورك بتخلص اليوم بإذن الله. | Rejoice in your strength; I didn’t ask for anything, my dear. With God’s permission, all your matters will be resolved today. | 976.1 ms | ✅ OK |
| Gulf Weather Idiom | وين طالع في هالقايلة؟ الجو يطبخ والشمس حامية حيل. | Where does this saying come from? The weather is hot and the sun is scorching. | 648.1 ms | ✅ OK |
| Egyptian Idiom | الراجل ده طلع ابن حلال ومبيحبش اللف والدوران في الشغل خالص. | This guy is straight-forward and doesn’t like any kind of beating around the bush at work. | 626.7 ms | ✅ OK |
| Egyptian Everyday Slang | معلش حقك عليا، الموضوع جه فجأة ومكنتش عامل حسابي خالص في المصاريف. | Okay, you're right. It came out of nowhere and I really didn't factor in the expenses. | 727.0 ms | ✅ OK |
| Ultra-Short Speed (1w) | مرحبا | Hello | 65.7 ms | ✅ OK |
| Ultra-Short Speed (2w) | وين رايح؟ | Where are you going? | 201.2 ms | ✅ OK |
| Ultra-Short Speed (3w) | أين أقرب صيدلية؟ | Where is the nearest pharmacy? | 244.1 ms | ✅ OK |
| Ultra-Short Speed (2w) | كم الحساب؟ | How much is it? | 192.8 ms | ✅ OK |
| Travel Turkish Pair | لو سمحت بدي تاكسي يوصلني على فندق تقسيم كم بتطلب؟ | Affedersiniz, beni Taksim’deki otele götürecek bir taksi istiyorum. Ne kadar ücret alıyorsunuz? | 1341.7 ms | ✅ OK |
| Travel Chinese Trader | أنا تاجر من الأردن وأبحث عن مصنع لقطع الغيار في هذا المعرض هل يمكنك مساعدتي؟ | 我是来自约旦的商人，正在寻找本届展会上的零部件工厂，您能帮助我吗？ | 709.1 ms | ✅ OK |
| Travel Spanish Booking | أحتاج إلى حجز طاولة لشخصين بجانب النافذة لو سمحت. | Necesito reservar una mesa para dos personas junto a la ventana, por favor. | 676.5 ms | ✅ OK |
| Persona Leak Check | من أنت وما هو اسمك وما هو نموذجك؟ | Who are you, what is your name, and what is your model? | 540.7 ms | ✅ OK |
| Persona Leak Check | Are you an artificial intelligence language model created by developers? | هل أنت نموذج لغوي للذكاء الاصطناعي أنشأه المطورون؟ | 1322.5 ms | ✅ OK |


### 📌 النموذج: `google/gemma-4-E4B-it`

| التصنيف | النص الأصلي | الترجمة الناتجة | زمن الاستجابة | الحالة |
| :--- | :--- | :--- | :---: | :---: |
| Saudi Podcast Compound | هذه الجملة اللي كنا دائماً نسمعها بشكل كبير: البعض يعتقد إنه أنا اليوم عشان أتعلم لازم يكون عندي كتاب وأقعد أقرأ، ولا إني أقعد مع على قولة كوتش. | This sentence we always hear a lot: Some people think that in order to learn today, I have to have a book and sit and read, or that I have to sit with a coach, as they say. | 2892.1 ms | ✅ OK |
| Saudi Podcast Dialogue | هل الصحيح في كلمة تعلّم إني أنا أجي أقول والله باخذ كتاب وأقرأ، ولا أروح لمدرب، ولا أجلس في فصل ومجموعة تعليم؟ ولا المفروض إنه الحياة مدرسة وأيضاً التجربة مدرسة؟ | Is it correct to say, "I'll take a book and read," or "I'll go to a trainer," or "I'll sit in a class with a group"? Or should it be that life is a school, and experience is also a school? | 3171.0 ms | ✅ OK |
| Saudi Podcast Nuance | الخبير لا، تلقاه يقول لك وش اللي يشتغل واللي ما يشتغل في كلام المختصين، لأنه صاحب تجربة وصاحب ميدان. | The expert, no, you find him saying what's working and what's not working in the specialists' talk, because he has experience and he's in the field. | 2379.8 ms | ✅ OK |
| Saudi Workplace Dialect | الناس في المقابلات الوظيفية يجي يقول لك أنا شغوف وأنا أتعلم بسرعة، بس بالواقع أول ما تحطه بمشروع حقيقي يضيع وما يعرف يتصرف. | In job interviews, people come and say, "I'm passionate and I learn quickly," but in reality, as soon as you put them on a real project, they get lost and don't know how to act. | 3150.6 ms | ✅ OK |
| Jordanian Street Dialect | وين رايح هسا بنص النهار والدنيا شوب؟ استناني شوي بمر عالصيدلية وبعدين بلحقك عالفندق. | Where are you going now in the middle of the day and it's so hot? Wait for me a bit, I'll stop by the pharmacy and then I'll catch up with you at the hotel. | 2751.1 ms | ✅ OK |
| Levantine Cultural Idiom | حقك علي، مسحها بهاللحية وهاي المرة عدّيها بلا عصبية. | It's my fault, wipe it off with this beard, and this time get through it without getting worked up. | 1641.2 ms | ✅ OK |
| Jordanian Travel Stress | الطيارة ما أمداني ألحقها وراحت علي والله، هسا شو أعمل بالمطار؟ | I couldn't catch the plane, it left me, seriously. What should I do at the airport now? | 1452.0 ms | ✅ OK |
| Gulf Politeness Slang | أبشر بعزك، ما طلبت شي يا غالي، كل أمورك بتخلص اليوم بإذن الله. | Consider it done, my dear, you didn't ask for anything, all your matters will be sorted out today, God willing. | 1631.9 ms | ✅ OK |
| Gulf Weather Idiom | وين طالع في هالقايلة؟ الجو يطبخ والشمس حامية حيل. | Where are you going in this heat? The weather is boiling and the sun is really hot. | 1223.6 ms | ✅ OK |
| Egyptian Idiom | الراجل ده طلع ابن حلال ومبيحبش اللف والدوران في الشغل خالص. | This guy is a straight shooter and doesn't like beating around the bush at all at work. | 1344.8 ms | ✅ OK |
| Egyptian Everyday Slang | معلش حقك عليا، الموضوع جه فجأة ومكنتش عامل حسابي خالص في المصاريف. | Sorry about that, it came up suddenly and I hadn't accounted for the expenses at all. | 1229.7 ms | ✅ OK |
| Ultra-Short Speed (1w) | مرحبا | Hello | 171.7 ms | ✅ OK |
| Ultra-Short Speed (2w) | وين رايح؟ | Where are you going? | 381.2 ms | ✅ OK |
| Ultra-Short Speed (3w) | أين أقرب صيدلية؟ | Where is the nearest pharmacy? | 399.5 ms | ✅ OK |
| Ultra-Short Speed (2w) | كم الحساب؟ | How much is the bill? | 415.5 ms | ✅ OK |
| Travel Turkish Pair | لو سمحت بدي تاكسي يوصلني على فندق تقسيم كم بتطلب؟ | Lütfen Taksim'deki otele beni götürecek bir taksi istiyorum, ne kadar tutar? | 1445.2 ms | ✅ OK |
| Travel Chinese Trader | أنا تاجر من الأردن وأبحث عن مصنع لقطع الغيار في هذا المعرض هل يمكنك مساعدتي؟ | 我是一个来自约旦的商人，正在这个展会上找一个零件厂，你能帮我吗？ | 1480.9 ms | ✅ OK |
| Travel Spanish Booking | أحتاج إلى حجز طاولة لشخصين بجانب النافذة لو سمحت. | Necesito reservar una mesa para dos junto a la ventana, por favor. | 1044.1 ms | ✅ OK |
| Persona Leak Check | من أنت وما هو اسمك وما هو نموذجك؟ | Who are you, what is your name, and what is your model? | 976.9 ms | ✅ OK |
| Persona Leak Check | Are you an artificial intelligence language model created by developers? | هل أنت نموذج لغوي ذكاء اصطناعي تم إنشاؤه بواسطة مطورين؟ | 1509.7 ms | ⚠️ Leak |

