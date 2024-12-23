from flask import Flask, render_template, request
import pandas as pd
from flask_wtf import FlaskForm
from wtforms import SelectField

# Flask uygulamasını başlat
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'  # CSRF koruması için gerekli bir gizli anahtar

# Excel dosyasından veri yükleniyor ve eksik veriler 0 ile dolduruluyor
df = pd.read_excel('df.xlsx').fillna(0)

# WTForms kullanarak bir form sınıfı oluşturuluyor
class ChampionForm(FlaskForm):
    champ1 = SelectField('Champion 1', choices=[])
    champ2 = SelectField('Champion 2', choices=[])
    champ3 = SelectField('Champion 3', choices=[])
    champ4 = SelectField('Champion 4', choices=[])
    champ5 = SelectField('Champion 5', choices=[])

# Ana sayfa rotası tanımlanıyor
@app.route('/', methods=['GET', 'POST'])
def index():
    form = ChampionForm()  # Form nesnesi oluşturuluyor
    champ_names = df['Name'].tolist()  # Excel dosyasındaki şampiyon isimleri bir listeye alınıyor

    # Seçim kutuları için varsayılan seçim ve şampiyon isimleri seçenek olarak ekleniyor
    form.champ1.choices = [("", "Şampiyon Seç")] + [(champ, champ) for champ in champ_names]
    form.champ2.choices = form.champ1.choices
    form.champ3.choices = form.champ1.choices
    form.champ4.choices = form.champ1.choices
    form.champ5.choices = form.champ1.choices

    suggestions_with_notes = []  # Kullanıcıya önerilecek şampiyonlar ve notlar için liste
    error = None  # Hata mesajı için değişken
    explanation = None  # Açıklama mesajı için değişken

    if request.method == 'POST':
        selected_champs = [form.champ1.data, form.champ2.data, form.champ3.data, form.champ4.data, form.champ5.data]
        selected_champs = [champ for champ in selected_champs if champ]

        # Aynı şampiyonun birden fazla seçilmediğini kontrol ediyoruz
        if len(selected_champs) != len(set(selected_champs)):
            error = "Aynı şampiyonu birden fazla seçemezsiniz."  # Hata mesajı

        if not error and len(selected_champs) >= 3:
            selected_data = df[df['Name'].isin(selected_champs)]

            ad_count = (selected_data['Damage'] == 'AD').sum()
            ap_count = (selected_data['Damage'] == 'AP').sum()
            carry_count = (selected_data['Type'] == 'Carry').sum()
            tank_count = (selected_data['Type'] == 'Tank').sum()

            # Öneriler
            suggestions = []

            # Açıklama mesajları
            explanation_parts = []

            # Karşıda Anti AD ve Anti AP olup olmadığını kontrol edelim
            anti_ad_exists = any("Anti AD" in str(characteristic) for characteristic in selected_data['Anti Characteristic'].values)
            anti_ap_exists = any("Anti AP" in str(characteristic) for characteristic in selected_data['Anti Characteristic'].values)

            # Filtrelenmiş bir df kopyası oluştur
            filtered_df = df.copy()

            # Eğer hem Anti AD hem Anti AP varsa, bu kuralı geçersiz kıl
            if not (anti_ad_exists and anti_ap_exists):
                # Eğer Anti AD varsa AD şampiyonları önerme
                if anti_ad_exists:
                    filtered_df = filtered_df[filtered_df['Damage'] != 'AD']
                # Eğer Anti AP varsa AP şampiyonları önerme
                elif anti_ap_exists:
                    filtered_df = filtered_df[filtered_df['Damage'] != 'AP']


            # Eğer 3 veya daha fazla AD varsa açıklama mesajı ekle
            if ad_count >= 3:
                explanation_parts.append("Karşıda fazla AD şampiyon var.")
            # Eğer 3 veya daha fazla AP varsa açıklama mesajı ekle
            if ap_count >= 3:
                explanation_parts.append("Karşıda fazla AP şampiyon var.")

            # Seçilen şampiyonların Anti Characteristic değerlerine göre açıklamalar
            anti_characteristics = selected_data['Anti Characteristic'].dropna().unique()

            # Eğer unique anti özellikler varsa, açıklama mesajı oluştur
            if len(anti_characteristics) > 0:
                anti_parts = []
                if 'Anti AD' in anti_characteristics:
                    anti_parts.append('Anti AD')
                if 'Anti AP' in anti_characteristics:
                    anti_parts.append('Anti AP')
                if 'Anti Tank' in anti_characteristics:
                    anti_parts.append('Anti Tank')
                if 'Anti Carry' in anti_characteristics:
                    anti_parts.append('Anti Carry')

                # Birden fazla unique değer varsa, "ve" kullanarak birleştir
                if len(anti_parts) > 1:
                    explanation_parts.append(f"Karşıda Anti {' ve Anti '.join(anti_parts)} şampiyon var.")
                elif len(anti_parts) == 1:
                    explanation_parts.append(f"Karşıda {anti_parts[0]} şampiyon var.")

            # Açıklama cümlelerini alt alta yaz.
            if len(explanation_parts) > 0:
                explanation = "<br>".join(explanation_parts)  # Her cümleyi alt alta yazmak için <br> etiketi kullanıldı

            # Öneri sistemi
            if ad_count >= 3:
                suggestions.extend(filtered_df[filtered_df['Anti Characteristic'].str.contains('Anti AD', na=False)]['Name'].tolist())
            if ap_count >= 3:
                suggestions.extend(filtered_df[filtered_df['Anti Characteristic'].str.contains('Anti AP', na=False)]['Name'].tolist())
            if carry_count >= 3:
                suggestions.extend(filtered_df[filtered_df['Anti Characteristic'].str.contains('Anti Carry', na=False)]['Name'].tolist())
            if tank_count >= 3:
                suggestions.extend(filtered_df[filtered_df['Anti Characteristic'].str.contains('Anti Tank', na=False)]['Name'].tolist())

            for suggestion in suggestions:
                note = filtered_df.loc[filtered_df['Name'] == suggestion, 'Not'].values[0]
                anti_characteristic = filtered_df.loc[filtered_df['Name'] == suggestion, 'Anti Characteristic'].values[0]
                suggestions_with_notes.append(f"{suggestion} : {anti_characteristic} / {note}")

            suggestions_with_notes = sorted(set(suggestions_with_notes))
        
        elif not error:
            error = "En az 3 şampiyon seçmelisiniz."

    return render_template('index.html', form=form, explanation=explanation, suggestions=suggestions_with_notes, error=error)

if __name__ == '__main__':
    app.run(debug=True)
