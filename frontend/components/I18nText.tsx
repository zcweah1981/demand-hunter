'use client'
import {useLang} from '../lib/i18n'
export function I18nText({zh,en}:{zh:string;en:string}){const {lang}=useLang(); return <>{lang==='en'?en:zh}</>}
